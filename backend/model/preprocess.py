import os
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

def main():
    # Define column names based on dataset documentation
    index_names = ['unit_number', 'time_in_cycles']
    setting_names = ['setting_1', 'setting_2', 'setting_3']
    sensor_names = [f's_{i}' for i in range(1, 22)]
    col_names = index_names + setting_names + sensor_names

    # Paths (relative to backend dir)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, "data", "raw")
    processed_dir = os.path.join(base_dir, "data", "processed")
    os.makedirs(processed_dir, exist_ok=True)


    # Load raw files
    train_path = os.path.join(raw_dir, 'train_FD001.txt')
    test_path = os.path.join(raw_dir, 'test_FD001.txt')
    rul_path = os.path.join(raw_dir, 'RUL_FD001.txt')

    if not os.path.exists(train_path):
        print(f"Error: {train_path} not found. Please download first.")
        return

    train_df = pd.read_csv(train_path, sep=r'\s+', header=None, names=col_names)
    test_df = pd.read_csv(test_path, sep=r'\s+', header=None, names=col_names)
    test_rul = pd.read_csv(rul_path, sep=r'\s+', header=None, names=['RUL'])

    # Standard C-MAPSS: Drop near-zero variance sensors and op settings
    sensors_to_drop = ['s_1', 's_5', 's_6', 's_10', 's_16', 's_18', 's_19']
    feature_cols = [s for s in sensor_names if s not in sensors_to_drop]
    train_df.drop(columns=sensors_to_drop + setting_names, inplace=True)
    test_df.drop(columns=sensors_to_drop + setting_names, inplace=True)

    # RUL Target capping
    def compute_rul(df, cap=125):
        max_cycle = df.groupby('unit_number')['time_in_cycles'].transform('max')
        df['RUL'] = (max_cycle - df['time_in_cycles']).clip(upper=cap)
        return df

    train_df = compute_rul(train_df)

    # Split by ENGINE ID to avoid data leakage
    unique_units = train_df['unit_number'].unique()
    train_units, val_units = train_test_split(unique_units, test_size=0.2, random_state=42)

    train_split = train_df[train_df['unit_number'].isin(train_units)].copy()
    val_split = train_df[train_df['unit_number'].isin(val_units)].copy()

    # Normalize based on TRAIN only
    scaler = StandardScaler()
    scaler.fit(train_split[feature_cols])

    # Save fitted scaler for deployment inference
    joblib.dump(scaler, os.path.join(processed_dir, 'scaler.joblib'))
    print("Saved StandardScaler to scaler.joblib")

    train_split[feature_cols] = scaler.transform(train_split[feature_cols])
    val_split[feature_cols] = scaler.transform(val_split[feature_cols])
    test_df[feature_cols] = scaler.transform(test_df[feature_cols])

    # Build sliding windows
    def build_windows(df, window=30, features=feature_cols, is_test=False):
        X, y = [], []
        for unit_id, group in df.groupby('unit_number'):
            group = group.sort_values('time_in_cycles')
            values = group[features].values
            
            # Handle short engines via padding
            if len(values) < window:
                pad_len = window - len(values)
                values = np.vstack([np.repeat(values[0:1], pad_len, axis=0), values])
                if not is_test:
                    labels = group['RUL'].values
                    labels = np.concatenate([np.repeat(labels[0], pad_len), labels])
            else:
                if not is_test: 
                    labels = group['RUL'].values

            if is_test:
                # Only the final window for official evaluation
                X.append(values[-window:])
            else:
                # Dense sliding windows for training
                for end in range(window, len(values) + 1):
                    X.append(values[end-window:end])
                    y.append(labels[end-1])
                    
        return np.array(X), np.array(y)

    SEQUENCE_LENGTH = 30
    x_train, y_train = build_windows(train_split)
    x_val, y_val = build_windows(val_split)
    x_test, _ = build_windows(test_df, is_test=True)

    # Align test labels
    y_test = test_rul['RUL'].clip(upper=125).values.astype(np.float32)

    # Save processed arrays
    np.save(os.path.join(processed_dir, 'x_train.npy'), x_train)
    np.save(os.path.join(processed_dir, 'y_train.npy'), y_train)
    np.save(os.path.join(processed_dir, 'x_val.npy'), x_val)
    np.save(os.path.join(processed_dir, 'y_val.npy'), y_val)
    np.save(os.path.join(processed_dir, 'x_test.npy'), x_test)
    np.save(os.path.join(processed_dir, 'y_test.npy'), y_test)
    
    # Save active feature list
    with open(os.path.join(processed_dir, 'active_features.txt'), 'w') as f:
        f.write('\n'.join(feature_cols))

    print(f"Data preprocessing complete.")
    print(f"X_train: {x_train.shape}, X_val: {x_val.shape}, X_test: {x_test.shape}")
    print(f"Sample window label: {y_train[0]}")

if __name__ == "__main__":
    main()
