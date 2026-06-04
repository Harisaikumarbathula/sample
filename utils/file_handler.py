import pandas as pd
import os
import traceback

def load_data(file):
    """
    Loads data from a CSV or Excel file.
    """
    file_extension = os.path.splitext(file.name)[1].lower()
    
    try:
        # Reset file pointer to the beginning before reading
        file.seek(0)
        
        if file_extension == '.csv':
            # Try loading with utf-8 first, fallback to latin1
            try:
                # Detect delimiter (comma, semicolon, or tab)
                # First try comma
                df = pd.read_csv(file)
                if len(df.columns) <= 1: # If only one column, maybe delimiter is wrong
                    file.seek(0)
                    df = pd.read_csv(file, sep=None, engine='python')
                return df
            except UnicodeDecodeError:
                file.seek(0) # Reset buffer
                return pd.read_csv(file, encoding='latin1', sep=None, engine='python')
        elif file_extension in ['.xlsx', '.xls']:
            file.seek(0)
            return pd.read_excel(file)
        else:
            print(f"Unsupported file extension: {file_extension}")
            return None
    except Exception as e:
        print(f"Error loading file: {e}")
        traceback.print_exc()
        return None

def save_data(df, file_path):
    """
    Saves a DataFrame to a CSV file.
    """
    try:
        df.to_csv(file_path, index=False)
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False
