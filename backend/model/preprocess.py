import os
import numpy as np
import pandas as pd

def load_data(raw_dir):
    columns = ['unit_id', 'time_cycles', 'op_setting_1', 'op_setting_2', 'op_setting_3'] + \
              [f'sensor_{i}' for i in range(1, 22)]
              
    train_path = os.path.join(raw_dir, 'train_FD001.txt')
    test_path = os.path.join(raw_dir, 'test_FD001.txt')
    rul_path = os.path.join(raw_dir, 'RUL_FD001.txt')
    
    train_df = pd.read_csv(train_path, sep=r'\s+', header=None, names=columns)
    test_df = pd.read_csv(test_path, sep=r'\s+', header=None, names=columns)
    
    # Load ground truth RUL for test engines
    rul_data = pd.read_csv(rul_path, sep=r'\s+', header=None, names=['RUL'])
    rul_data['unit_id'] = rul_data.index + 1
    
    return train_df, test_df, rul_data

def preprocess_data(train_df, test_df, rul_data, window_size=30, max_rul=125):
    # Features are op_settings + sensors
    feature_cols = ['op_setting_1', 'op_setting_2', 'op_setting_3'] + [f'sensor_{i}' for i in range(1, 22)]
    
    # 1. Identify low-variance sensors (threshold 1e-4)
    variances = train_df[feature_cols].var()
    low_var_cols = variances[variances < 1e-4].index.tolist()
    print(f"Dropping low variance columns: {low_var_cols}")
    
    active_features = [col for col in feature_cols if col not in low_var_cols]
    print(f"Active features ({len(active_features)}): {active_features}")
    
    # 2. Fit Min-Max Scaler on train active features
    min_vals = train_df[active_features].min()
    max_vals = train_df[active_features].max()
    
    # Avoid division by zero
    range_vals = max_vals - min_vals
    range_vals[range_vals == 0] = 1.0
    
    train_scaled = train_df.copy()
    test_scaled = test_df.copy()
    
    train_scaled[active_features] = (train_df[active_features] - min_vals) / range_vals
    test_scaled[active_features] = (test_df[active_features] - min_vals) / range_vals
    
    # Save min/max values for edge inference scaling
    processed_dir = "/home/saran/project/TwinEdge/backend/data/processed"
    os.makedirs(processed_dir, exist_ok=True)
    
    scaling_params = pd.DataFrame({'min': min_vals, 'max': max_vals, 'range': range_vals})
    scaling_params.to_csv(os.path.join(processed_dir, 'scaling_params.csv'))
    print(f"Saved scaling parameters to scaling_params.csv")
    
    # 3. Compute RUL labels
    # For training data, RUL is max_cycle - current_cycle (capped at max_rul)
    train_rul = []
    for unit_id, group in train_scaled.groupby('unit_id'):
        max_cycle = group['time_cycles'].max()
        rul = max_cycle - group['time_cycles']
        rul = np.clip(rul, 0, max_rul)
        train_rul.extend(rul.tolist())
    train_scaled['RUL'] = train_rul
    
    # For test data, RUL is (ground_truth_RUL + max_cycle_of_unit) - current_cycle (capped)
    test_rul = []
    rul_dict = dict(zip(rul_data['unit_id'], rul_data['RUL']))
    for unit_id, group in test_scaled.groupby('unit_id'):
        max_cycle = group['time_cycles'].max()
        gt_rul = rul_dict[unit_id]
        rul = (gt_rul + max_cycle) - group['time_cycles']
        rul = np.clip(rul, 0, max_rul)
        test_rul.extend(rul.tolist())
    test_scaled['RUL'] = test_rul
    
    # 4. Generate sliding windows
    def gen_sequence(df, seq_length, seq_cols):
        data_matrix = df[seq_cols].values
        num_elements = data_matrix.shape[0]
        for start, stop in zip(range(0, num_elements - seq_length + 1), range(seq_length, num_elements + 1)):
            yield data_matrix[start:stop, :]
            
    def gen_labels(df, seq_length, label_col):
        data_matrix = df[label_col].values
        num_elements = data_matrix.shape[0]
        return data_matrix[seq_length - 1:]
        
    X_train, y_train = [], []
    for unit_id, group in train_scaled.groupby('unit_id'):
        for seq in gen_sequence(group, window_size, active_features):
            X_train.append(seq)
        y_train.extend(gen_labels(group, window_size, 'RUL'))
        
    X_test, y_test = [], []
    for unit_id, group in test_scaled.groupby('unit_id'):
        for seq in gen_sequence(group, window_size, active_features):
            X_test.append(seq)
        y_test.extend(gen_labels(group, window_size, 'RUL'))
        
    X_train = np.array(X_train, dtype=np.float32)
    y_train = np.array(y_train, dtype=np.float32)
    X_test = np.array(X_test, dtype=np.float32)
    y_test = np.array(y_test, dtype=np.float32)
    
    return X_train, y_train, X_test, y_test, active_features

def main():
    raw_dir = "/home/saran/project/TwinEdge/backend/data/raw"
    processed_dir = "/home/saran/project/TwinEdge/backend/data/processed"
    
    train_df, test_df, rul_data = load_data(raw_dir)
    X_train, y_train, X_test, y_test, active_features = preprocess_data(train_df, test_df, rul_data)
    
    np.save(os.path.join(processed_dir, 'X_train.npy'), X_train)
    np.save(os.path.join(processed_dir, 'y_train.npy'), y_train)
    np.save(os.path.join(processed_dir, 'X_test.npy'), X_test)
    np.save(os.path.join(processed_dir, 'y_test.npy'), y_test)
    
    # Save active feature list
    with open(os.path.join(processed_dir, 'active_features.txt'), 'w') as f:
        f.write('\n'.join(active_features))
        
    print(f"Data preprocessing complete.")
    print(f"X_train shape: {X_train.shape}, y_train shape: {y_train.shape}")
    print(f"X_test shape: {X_test.shape}, y_test shape: {y_test.shape}")
    print(f"Sample window label: {y_train[0]}")

if __name__ == "__main__":
    main()
