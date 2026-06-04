import pandas as pd
import numpy as np

def remove_duplicates(df):
    """
    Removes duplicate rows from the DataFrame.
    """
    return df.drop_duplicates()

def handle_missing_values(df, column, strategy='mean', custom_value='Unknown'):
    """
    Handles missing values for a given column using the specified strategy.
    Strategies: 'mean', 'median', 'mode', 'forward_fill', 'backward_fill', 'constant', 'custom_constant'
    """
    df_copy = df.copy()
    
    if strategy == 'mean':
        if pd.api.types.is_numeric_dtype(df_copy[column]):
            df_copy[column] = df_copy[column].fillna(df_copy[column].mean())
    elif strategy == 'median':
        if pd.api.types.is_numeric_dtype(df_copy[column]):
            df_copy[column] = df_copy[column].fillna(df_copy[column].median())
    elif strategy == 'mode':
        mode_val = df_copy[column].mode()
        fill_val = mode_val[0] if not mode_val.empty else 'N/A'
        df_copy[column] = df_copy[column].fillna(fill_val)
    elif strategy == 'forward_fill':
        df_copy[column] = df_copy[column].ffill()
    elif strategy == 'backward_fill':
        df_copy[column] = df_copy[column].bfill()
    elif strategy == 'constant':
        df_copy[column] = df_copy[column].fillna('N/A')
    elif strategy == 'custom_constant':
        df_copy[column] = df_copy[column].fillna(custom_value)
        
    return df_copy

def clean_dataset(df, strategies=None):
    """
    Cleans the entire dataset based on the provided strategies.
    Strategies should be a dictionary: {column_name: strategy}
    """
    df_clean = df.copy()
    
    # 1. Remove duplicates
    df_clean = remove_duplicates(df_clean)
    
    # 2. Handle missing values
    if strategies:
        for column, strategy in strategies.items():
            if column in df_clean.columns:
                df_clean = handle_missing_values(df_clean, column, strategy)
                
    return df_clean
