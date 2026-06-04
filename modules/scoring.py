import pandas as pd
import numpy as np

def calculate_quality_score(df):
    """
    Calculates a data quality score (percentage).
    Ensures all inputs are safe for numeric operations and round().
    """
    try:
        # 1. Error handling for empty DataFrame
        if df is None or df.empty:
            return 0.0
            
        total_rows = int(len(df))
        total_cells = int(df.size)
        
        if total_cells == 0:
            return 0.0
        
        # 2. Total missing values calculation (safe int conversion)
        missing_cells = int(df.isnull().sum().sum())
        missing_ratio = float(missing_cells / total_cells)
        missing_score = (1.0 - missing_ratio) * 100.0
        
        # 3. Total duplicate rows calculation (safe int conversion)
        duplicates = int(df.duplicated().sum())
        duplicate_ratio = float(duplicates / total_rows) if total_rows > 0 else 0.0
        duplicate_score = (1.0 - duplicate_ratio) * 100.0
        
        # 4. Data completeness calculation
        non_null_count = int(df.notnull().sum(axis=0).sum())
        completeness_score = float(non_null_count / total_cells) * 100.0
        
        # 5. Overall weighted score
        # Using float() ensures no numpy.bool or other types are passed to round()
        overall_score = float((missing_score * 0.4) + (duplicate_score * 0.3) + (completeness_score * 0.3))
        
        return round(overall_score, 2)
        
    except Exception as e:
        print(f"Error in calculate_quality_score: {e}")
        return 0.0

def column_wise_metrics(df):
    """
    Returns a dictionary of quality metrics for each column.
    Ensures safe division and rounding.
    """
    metrics = {}
    try:
        if df is None or df.empty:
            return {}
            
        total_rows = len(df)
        for column in df.columns:
            missing_count = int(df[column].isnull().sum())
            missing_pct = float((missing_count / total_rows) * 100.0) if total_rows > 0 else 0.0
            
            metrics[column] = {
                'missing_count': missing_count,
                'missing_percentage': round(missing_pct, 2),
                'data_type': str(df[column].dtype)
            }
    except Exception as e:
        print(f"Error in column_wise_metrics: {e}")
        
    return metrics
