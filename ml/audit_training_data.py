
import pandas as pd

from ml.extract_training_data import extract_training_data


df = extract_training_data()

print("\nClosure-duration percentiles (hours):")
print(
    df["closure_hours"]
    .quantile([0.50, 0.75, 0.90, 0.95, 0.99, 0.999])
    .to_string()
)

print("\nRecords above selected thresholds:")
for threshold in [24, 168, 720, 2160, 8760]:
    count = int((df["closure_hours"] > threshold).sum())
    pct = count / len(df) * 100
    print(f">{threshold:>5} hours: {count:>7,} ({pct:.3f}%)")

print("\nLongest-duration records:")
print(
    df.nlargest(10, "closure_hours")[
        ["unique_key", "created_date", "complaint_type", "agency",
         "borough", "closure_hours"]
    ].to_string(index=False)
)

print("\nRecords by creation year:")
print(df.groupby(df["created_date"].dt.year).size().to_string())
