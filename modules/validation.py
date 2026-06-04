import pandas as pd
import numpy as np
import re

def detect_missing_values(df):
    """
    Returns a dictionary of missing value counts per column.
    """
    return df.isnull().sum().to_dict()

def detect_duplicates(df):
    """
    Returns the number of duplicate rows.
    """
    return df.duplicated().sum()

def validate_format(series, format_type):
    """
    Validates the format of a pandas series using regex.
    """
    regex_patterns = {
        'email': r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
        'phone': r'^\+?1?\d{9,15}$',
        'date': r'^\d{4}-\d{2}-\d{2}$' # YYYY-MM-DD format
    }
    
    pattern = regex_patterns.get(format_type)
    if not pattern:
        return None
    
    # Check if each value matches the pattern
    valid_mask = series.astype(str).str.match(pattern)
    return (~valid_mask).sum() # Return number of invalid entries

def validate_range(series, min_val, max_val):
    """
    Returns the number of values outside the specified numeric range.
    """
    if not pd.api.types.is_numeric_dtype(series):
        return None
    
    out_of_range = ((series < min_val) | (series > max_val)).sum()
    return out_of_range

def suggest_validation_rules(df):
    """
    Suggests validation rules based on column names and data types.
    """
    suggestions = {}
    
    for column in df.columns:
        col_name = column.lower()
        col_type = df[column].dtype
        
        if 'email' in col_name:
            suggestions[column] = {'type': 'format', 'format': 'email'}
        elif 'phone' in col_name or 'mobile' in col_name:
            suggestions[column] = {'type': 'format', 'format': 'phone'}
        elif 'date' in col_name or 'time' in col_name:
            suggestions[column] = {'type': 'format', 'format': 'date'}
        elif pd.api.types.is_numeric_dtype(col_type) and not pd.api.types.is_bool_dtype(col_type):
            suggestions[column] = {'type': 'range', 'min': float(df[column].min()), 'max': float(df[column].max())}
            
    return suggestions

def predict_potential_errors(df):
    """
    Predicts potential data errors based on heuristics.
    (Basic ML logic as requested - placeholder/heuristic based)
    """
    errors = []
    
    # 1. Outlier detection based on Z-score (simple ML logic)
    for column in df.select_dtypes(include=[np.number]).columns:
        mean = df[column].mean()
        std = df[column].std()
        if std > 0:
            z_scores = (df[column] - mean) / std
            outliers = (np.abs(z_scores) > 3).sum()
            if outliers > 0:
                errors.append(f"Potential outliers detected in column '{column}': {outliers} values.")
    
    # 2. Mixed data type detection
    for column in df.columns:
        types = df[column].apply(type).nunique()
        if types > 1:
            errors.append(f"Mixed data types detected in column '{column}'.")
            
    return errors
