from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import os
import pandas as pd
import numpy as np
import sqlite3
import json
from datetime import datetime
from utils.file_handler import load_data, save_data
from modules.validation import suggest_validation_rules, predict_potential_errors, detect_duplicates
from modules.cleaning import handle_missing_values, remove_duplicates
from modules.anomaly import detect_anomalies
from modules.scoring import calculate_quality_score, column_wise_metrics
from utils.report_generator import generate_report

app = Flask(__name__)
app.secret_key = 'enterprise_data_quality_management_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['DATABASE'] = 'database.db'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                quality_score REAL,
                row_count INTEGER,
                col_count INTEGER
            )
        ''')
        conn.commit()

init_db()

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/')
def index():
    return render_template('index.html', active_page='upload')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('index'))
    
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        # Load data to get initial stats
        df = load_data(file) # file is a FileStorage object, load_data might need a tweak or filepath
        # Re-load from path to be safe
        df = pd.read_csv(filepath) if filepath.endswith('.csv') else pd.read_excel(filepath)
        
        if df is not None:
            quality_score = calculate_quality_score(df)
            
            # Save to DB
            with get_db() as conn:
                cursor = conn.execute(
                    'INSERT INTO uploads (filename, quality_score, row_count, col_count) VALUES (?, ?, ?, ?)',
                    (file.filename, quality_score, len(df), len(df.columns))
                )
                upload_id = cursor.lastrowid
                conn.commit()
            
            session['current_file'] = filepath
            session['upload_id'] = upload_id
            
            flash(f'File {file.filename} uploaded and analyzed successfully!', 'success')
            return redirect(url_for('dashboard'))
            
    flash('File upload failed', 'danger')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'current_file' not in session:
        flash('Please upload a file first', 'warning')
        return redirect(url_for('index'))
    
    filepath = session['current_file']
    df = pd.read_csv(filepath) if filepath.endswith('.csv') else pd.read_excel(filepath)
    
    quality_score = calculate_quality_score(df)
    metrics = column_wise_metrics(df)
    suggestions = suggest_validation_rules(df)
    
    # Anomaly detection
    anomalies = detect_anomalies(df)
    total_anomalies = anomalies.sum() if anomalies is not None else 0
    
    # Prepare chart data
    missing_labels = list(metrics.keys())
    missing_values = [m['missing_count'] for m in metrics.values()]
    
    total_cells = df.size
    total_missing = sum(missing_values)
    missing_percent = round((total_missing / total_cells) * 100, 2) if total_cells > 0 else 0
    
    total_duplicates = detect_duplicates(df)
    duplicate_percent = round((total_duplicates / len(df)) * 100, 2) if len(df) > 0 else 0

    return render_template('dashboard.html', 
                           active_page='dashboard',
                           file_name=os.path.basename(filepath),
                           row_count=len(df),
                           col_count=len(df.columns),
                           quality_score=quality_score,
                           total_missing=total_missing,
                           missing_percent=missing_percent,
                           total_duplicates=total_duplicates,
                           duplicate_percent=duplicate_percent,
                           total_anomalies=total_anomalies,
                           suggestions=suggestions,
                           missing_labels=missing_labels,
                           missing_values=missing_values,
                           table_html=df.head(10).to_html(classes='table table-hover table-striped mb-0'))

@app.route('/cleaning', methods=['GET', 'POST'])
def cleaning():
    if 'current_file' not in session:
        flash('Please upload a file first', 'warning')
        return redirect(url_for('index'))
    
    filepath = session['current_file']
    df = pd.read_csv(filepath) if filepath.endswith('.csv') else pd.read_excel(filepath)
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'remove_duplicates':
            df = remove_duplicates(df)
            flash('Duplicates removed successfully!', 'success')
        elif action == 'fill_missing':
            col = request.form.get('column')
            strategy = request.form.get('strategy')
            df = handle_missing_values(df, col, strategy)
            flash(f'Missing values in {col} handled using {strategy}', 'success')
        
        # Save updated data
        df.to_csv(filepath, index=False)
        return redirect(url_for('cleaning'))

    return render_template('cleaning.html', 
                           active_page='cleaning',
                           columns=df.columns.tolist(),
                           table_html=df.head(10).to_html(classes='table table-sm table-hover'))

@app.route('/reports')
def reports():
    if 'current_file' not in session:
        flash('Please upload a file first', 'warning')
        return redirect(url_for('index'))
    
    filepath = session['current_file']
    df = pd.read_csv(filepath) if filepath.endswith('.csv') else pd.read_excel(filepath)
    
    quality_score = calculate_quality_score(df)
    metrics = column_wise_metrics(df)
    errors = predict_potential_errors(df)
    
    report_path = generate_report(df, os.path.basename(filepath), metrics, quality_score, errors)
    
    # We might want to list all reports or just provide a download for the latest one
    return render_template('reports.html', 
                           active_page='reports',
                           report_ready=True,
                           report_filename=os.path.basename(report_path))

@app.route('/download_report/<filename>')
def download_report(filename):
    return send_file(os.path.join(app.config['OUTPUT_FOLDER'], filename), as_attachment=True)

@app.route('/download_data')
def download_data():
    if 'current_file' not in session:
        return redirect(url_for('index'))
    return send_file(session['current_file'], as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
