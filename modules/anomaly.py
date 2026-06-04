import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

def detect_anomalies(df, contamination=0.05):
    """
    Detects anomalies in numeric columns using Isolation Forest.
    Returns a DataFrame with an 'is_anomaly' column (True for anomalies, False for normal).
    """
    # Select numeric columns for anomaly detection
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if not numeric_cols:
        return None
    
    # Handle missing values for anomaly detection (Isolation Forest doesn't like NaNs)
    df_numeric = df[numeric_cols].fillna(df[numeric_cols].mean())
    
    # Scale numeric data
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df_numeric)
    
    # Fit Isolation Forest model
    clf = IsolationForest(contamination=contamination, random_state=42)
    preds = clf.fit_predict(scaled_data)
    
    # 1 is normal, -1 is anomaly
    return preds == -1
