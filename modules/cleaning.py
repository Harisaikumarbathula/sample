import pandas as pd
import numpy as np

def remove_duplicates(df):
    """
    Removes duplicate rows from the DataFrame.
    """
    return df.drop_duplicates()

def handle_missing_values(df, column, strategy='mean'):
    """
    Handles missing values for a given column using the specified strategy.
    Strategies: 'mean', 'median', 'forward_fill', 'backward_fill', 'constant'
    """
    df_copy = df.copy()
    
    if strategy == 'mean':
        if pd.api.types.is_numeric_dtype(df_copy[column]):
            df_copy[column] = df_copy[column].fillna(df_copy[column].mean())
    elif strategy == 'median':
        if pd.api.types.is_numeric_dtype(df_copy[column]):
            df_copy[column] = df_copy[column].fillna(df_copy[column].median())
    elif strategy == 'forward_fill':
        df_copy[column] = df_copy[column].ffill()
    elif strategy == 'backward_fill':
        df_copy[column] = df_copy[column].bfill()
    elif strategy == 'constant':
        df_copy[column] = df_copy[column].fillna('N/A')
        
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
