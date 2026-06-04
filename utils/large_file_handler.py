import os
import sqlite3
import pandas as pd
import numpy as np
import hashlib
import json
import traceback
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

def detect_delimiter(filepath):
    """
    Detects the delimiter of a text/CSV file by reading the header.
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            header = f.readline()
        
        delimiters = [',', ';', '\t', '|']
        best_delim = ','
        max_cols = 1
        
        for d in delimiters:
            cols = len(header.split(d))
            if cols > max_cols:
                max_cols = cols
                best_delim = d
        return best_delim
    except Exception:
        return ','

def get_file_preview(filepath, nrows=10):
    """
    Returns a HTML preview of the first nrows of the dataset.
    """
    delim = detect_delimiter(filepath)
    try:
        df = pd.read_csv(filepath, sep=delim, nrows=nrows)
        return df.to_html(classes='table table-hover table-striped mb-0')
    except Exception as e:
        return f"<div class='alert alert-danger'>Error generating preview: {str(e)}</div>"

def analyze_large_file_async(db_path, upload_id, filepath):
    """
    Runs in a background thread. Reads the file in chunks and updates the database with progress and final results.
    """
    conn = None
    try:
        update_job_status(db_path, upload_id, 'processing', 5.0)
        
        delim = detect_delimiter(filepath)
        file_size_bytes = os.path.getsize(filepath)
        
        # 1. Read a small sample (first 100k rows) to infer schema and train anomaly detection
        sample_rows = 100000
        try:
            sample_df = pd.read_csv(filepath, sep=delim, nrows=sample_rows)
        except Exception as e:
            update_job_status(db_path, upload_id, 'failed', 0.0, f"Failed to read file header/sample: {str(e)}")
            return
            
        columns = sample_df.columns.tolist()
        col_count = len(columns)
        numeric_cols = sample_df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Fit Isolation Forest and scaler on sample if we have numeric columns
        scaler = None
        clf = None
        if numeric_cols:
            update_job_status(db_path, upload_id, 'processing', 15.0)
            sample_numeric = sample_df[numeric_cols].fillna(sample_df[numeric_cols].mean())
            if not sample_numeric.empty:
                scaler = StandardScaler()
                scaled_data = scaler.fit_transform(sample_numeric)
                clf = IsolationForest(contamination=0.05, random_state=42)
                clf.fit(scaled_data)

        # Create a temp SQLite table to store row hashes for deduplication
        conn = sqlite3.connect(db_path, timeout=30.0)
        cursor = conn.cursor()
        hash_table_name = f"temp_hashes_{upload_id}"
        cursor.execute(f"DROP TABLE IF EXISTS {hash_table_name}")
        cursor.execute(f"CREATE TABLE {hash_table_name} (hash TEXT PRIMARY KEY)")
        conn.commit()

        # Initialize chunked statistics counters
        total_rows = 0
        missing_counts = {col: 0 for col in columns}
        numeric_sums = {col: 0.0 for col in numeric_cols}
        numeric_counts = {col: 0 for col in numeric_cols}
        numeric_mins = {col: float('inf') for col in numeric_cols}
        numeric_maxs = {col: float('-inf') for col in numeric_cols}
        anomalies_count = 0
        
        # Suggest validation rules based on sample
        from modules.validation import suggest_validation_rules
        suggestions = suggest_validation_rules(sample_df)
        
        # Estimate file size in chunks
        # Let's estimate total chunks. We read in chunks of 100,000 rows.
        # Estimate average row size from sample
        sample_size_bytes = sample_df.memory_usage(deep=True).sum()
        avg_row_size = sample_size_bytes / len(sample_df) if len(sample_df) > 0 else 100
        # Estimate total rows based on file size and average row size
        estimated_total_rows = max(1, int(file_size_bytes / (avg_row_size * 0.8))) # Adjusting for CSV string representation density
        chunk_size = 100000
        
        # Process file chunk by chunk
        chunks_generator = pd.read_csv(filepath, sep=delim, chunksize=chunk_size)
        
        update_job_status(db_path, upload_id, 'processing', 20.0)
        
        for i, chunk in enumerate(chunks_generator):
            chunk_len = len(chunk)
            if chunk_len == 0:
                continue
                
            total_rows += chunk_len
            
            # Missing values
            for col in columns:
                missing_counts[col] += int(chunk[col].isnull().sum())
                
            # Numeric stats
            for col in numeric_cols:
                non_null_chunk = chunk[col].dropna()
                numeric_sums[col] += float(non_null_chunk.sum())
                numeric_counts[col] += int(non_null_chunk.count())
                if not non_null_chunk.empty:
                    numeric_mins[col] = min(numeric_mins[col], float(non_null_chunk.min()))
                    numeric_maxs[col] = max(numeric_maxs[col], float(non_null_chunk.max()))
                    
            # Anomaly prediction (Isolation Forest)
            if clf and scaler and numeric_cols:
                chunk_numeric = chunk[numeric_cols].fillna(sample_df[numeric_cols].mean())
                if not chunk_numeric.empty:
                    scaled_chunk = scaler.transform(chunk_numeric)
                    preds = clf.predict(scaled_chunk)
                    anomalies_count += int((preds == -1).sum())
                    
            # Hash rows and insert to SQLite for deduplication
            # Convert rows to string to get a unique hash
            row_hashes = []
            for row in chunk.values:
                row_str = "".join(str(val) for val in row)
                h = hashlib.md5(row_str.encode('utf-8', errors='ignore')).hexdigest()
                row_hashes.append((h,))
                
            cursor.executemany(f"INSERT OR IGNORE INTO {hash_table_name} VALUES (?)", row_hashes)
            
            # Periodically commit and update progress
            if i % 5 == 0:
                conn.commit()
                # Calculate progress: from 20% to 90%
                processed_ratio = min(0.99, total_rows / estimated_total_rows)
                progress_val = 20.0 + (processed_ratio * 70.0)
                update_job_status(db_path, upload_id, 'processing', round(progress_val, 1))

        # End of file traversal, complete calculations
        conn.commit()
        
        # Calculate duplicates
        total_unique_rows = cursor.execute(f"SELECT COUNT(*) FROM {hash_table_name}").fetchone()[0]
        duplicate_count = max(0, total_rows - total_unique_rows)
        
        # Drop temporary table
        cursor.execute(f"DROP TABLE IF EXISTS {hash_table_name}")
        conn.commit()
        conn.close()
        conn = None

        # Build column metrics dictionary
        metrics = {}
        for col in columns:
            missing_count = missing_counts[col]
            missing_pct = float((missing_count / total_rows) * 100.0) if total_rows > 0 else 0.0
            data_type = str(sample_df[col].dtype)
            metrics[col] = {
                'missing_count': missing_count,
                'missing_percentage': round(missing_pct, 2),
                'data_type': data_type
            }
            
        # Calculate Quality Score
        total_cells = total_rows * col_count
        missing_cells = sum(missing_counts.values())
        missing_ratio = float(missing_cells / total_cells) if total_cells > 0 else 0.0
        missing_score = (1.0 - missing_ratio) * 100.0
        
        duplicate_ratio = float(duplicate_count / total_rows) if total_rows > 0 else 0.0
        duplicate_score = (1.0 - duplicate_ratio) * 100.0
        
        completeness_score = float((total_cells - missing_cells) / total_cells) * 100.0 if total_cells > 0 else 0.0
        overall_score = float((missing_score * 0.4) + (duplicate_score * 0.3) + (completeness_score * 0.3))
        quality_score = round(overall_score, 2)
        
        # Predict potential errors (heuristics)
        errors = []
        for col in numeric_cols:
            # We can calculate means and check for range/outliers using standard deviation
            # For std, we need another pass, or we can use the anomaly score.
            # Let's say if we have anomalies, we note it.
            pass
        if anomalies_count > 0:
            errors.append(f"Potential outliers/anomalies detected: {anomalies_count} records.")
            
        for col in columns:
            # Mixed type detection from sample
            types = sample_df[col].apply(type).nunique()
            if types > 1:
                errors.append(f"Mixed data types detected in column '{col}'.")
                
        # Calculate column means to store in database for quick imputation later
        column_stats = {}
        for col in numeric_cols:
            cnt = numeric_counts[col]
            column_stats[col] = {
                'mean': float(numeric_sums[col] / cnt) if cnt > 0 else 0.0,
                'min': numeric_mins[col],
                'max': numeric_maxs[col]
            }

        # Save all results to the database
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.execute('''
            UPDATE uploads 
            SET quality_score = ?, row_count = ?, col_count = ?, status = 'completed', progress = 100.0,
                column_metrics = ?, suggestions = ?, anomalies_count = ?, duplicate_count = ?, errors = ?, file_path = ?
            WHERE id = ?
        ''', (
            quality_score, total_rows, col_count,
            json.dumps(metrics), json.dumps(suggestions), anomalies_count, duplicate_count, json.dumps(errors), filepath,
            upload_id
        ))
        # Store column_stats or other sidecar info in metadata if needed, let's keep it in a small json sidecar
        metadata_filepath = filepath + ".meta.json"
        with open(metadata_filepath, 'w') as f:
            json.dump({
                'column_stats': column_stats,
                'numeric_cols': numeric_cols,
                'columns': columns
            }, f)
            
        conn.commit()
        
    except Exception as e:
        traceback.print_exc()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS temp_hashes_{upload_id}")
                conn.commit()
            except Exception:
                pass
        update_job_status(db_path, upload_id, 'failed', 0.0, f"Error during processing: {str(e)}")
    finally:
        if conn:
            conn.close()

def clean_large_file_async(db_path, upload_id, input_filepath, output_filepath, operations):
    """
    Cleans a large file chunk by chunk and streams the result.
    Operations is a dict, e.g., {'remove_duplicates': True, 'fill_missing': {'column': 'Age', 'strategy': 'mean'}}
    """
    try:
        update_job_status(db_path, upload_id, 'processing', 10.0)
        
        delim = detect_delimiter(input_filepath)
        
        # Load metadata sidecar if exists to fetch column stats (e.g. means)
        column_stats = {}
        metadata_filepath = input_filepath + ".meta.json"
        if os.path.exists(metadata_filepath):
            with open(metadata_filepath, 'r') as f:
                metadata = json.load(f)
                column_stats = metadata.get('column_stats', {})
                
        # Deduplication setup if requested
        remove_dup = operations.get('remove_duplicates', False)
        hash_table_name = f"clean_hashes_{upload_id}"
        if remove_dup:
            conn = sqlite3.connect(db_path, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {hash_table_name}")
            cursor.execute(f"CREATE TABLE {hash_table_name} (hash TEXT PRIMARY KEY)")
            conn.commit()
            conn.close()

        # Fill missing setups
        fill_missing = operations.get('fill_missing', None)
        
        # Read and write chunk by chunk
        chunk_size = 100000
        chunks_generator = pd.read_csv(input_filepath, sep=delim, chunksize=chunk_size)
        
        write_header = True
        
        # Count total lines for progress
        total_input_rows = 0
        
        for i, chunk in enumerate(chunks_generator):
            chunk_len = len(chunk)
            total_input_rows += chunk_len
            
            # 1. Apply missing value imputations
            if fill_missing:
                col = fill_missing.get('column')
                strategy = fill_missing.get('strategy')
                if col in chunk.columns:
                    if strategy == 'mean':
                        mean_val = column_stats.get(col, {}).get('mean', 0.0)
                        chunk[col] = chunk[col].fillna(mean_val)
                    elif strategy == 'median':
                        median_val = column_stats.get(col, {}).get('median', chunk[col].median())
                        chunk[col] = chunk[col].fillna(median_val)
                    elif strategy == 'forward_fill':
                        chunk[col] = chunk[col].ffill()
                    elif strategy == 'backward_fill':
                        chunk[col] = chunk[col].bfill()
                    elif strategy == 'constant':
                        chunk[col] = chunk[col].fillna('N/A')
            
            # 2. Deduplication
            if remove_dup:
                row_hashes = []
                for row in chunk.values:
                    row_str = "".join(str(val) for val in row)
                    h = hashlib.md5(row_str.encode('utf-8', errors='ignore')).hexdigest()
                    row_hashes.append(h)
                
                # Check unique hashes using a fresh connection
                conn_tmp = sqlite3.connect(db_path, timeout=30.0)
                cursor_tmp = conn_tmp.cursor()
                
                unique_chunk_mask = []
                for h in row_hashes:
                    try:
                        cursor_tmp.execute(f"INSERT INTO {hash_table_name} VALUES (?)", (h,))
                        unique_chunk_mask.append(True)
                    except sqlite3.IntegrityError:
                        unique_chunk_mask.append(False)
                
                conn_tmp.commit()
                conn_tmp.close()
                
                chunk = chunk[unique_chunk_mask]
                
            # Write to output file
            chunk.to_csv(output_filepath, index=False, mode='a' if not write_header else 'w', header=write_header)
            write_header = False
            
            # Update progress
            progress_val = min(95.0, 10.0 + (i + 1) * 10.0)
            update_job_status(db_path, upload_id, 'processing', round(progress_val, 1))

        # Cleanup de-duplication table
        if remove_dup:
            conn_cleanup = sqlite3.connect(db_path, timeout=30.0)
            cursor_cleanup = conn_cleanup.cursor()
            cursor_cleanup.execute(f"DROP TABLE IF EXISTS {hash_table_name}")
            conn_cleanup.commit()
            conn_cleanup.close()
            
        # Run analyze on the cleaned file to update dashboard stats!
        analyze_large_file_async(db_path, upload_id, output_filepath)
        
    except Exception as e:
        traceback.print_exc()
        try:
            conn_err = sqlite3.connect(db_path, timeout=30.0)
            cursor_err = conn_err.cursor()
            cursor_err.execute(f"DROP TABLE IF EXISTS clean_hashes_{upload_id}")
            conn_err.commit()
            conn_err.close()
        except Exception:
            pass
        update_job_status(db_path, upload_id, 'failed', 0.0, f"Error during cleaning: {str(e)}")

def update_job_status(db_path, upload_id, status, progress, error_message=None):
    """
    Updates the status and progress of a background job.
    """
    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.execute('''
            UPDATE uploads 
            SET status = ?, progress = ?, error_message = ?
            WHERE id = ?
        ''', (status, progress, error_message, upload_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to update job status: {e}")
