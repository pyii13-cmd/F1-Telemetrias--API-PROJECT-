"""
Data Preprocessing Module - Clean and filter F1 lap data for degradation analysis.
"""
import pandas as pd
from typing import Tuple
import logging

# DISABLE ALL LOGGING
logging.basicConfig(level=logging.CRITICAL, handlers=[logging.NullHandler()])
for logger_name in ['fastf1', 'fastf1.core', 'fastf1.api']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

# Override print to catch any remaining Unicode
_original_print = print
def _safe_print(*args, **kwargs):
    try:
        _original_print(*args, **kwargs)
    except Exception:
        pass
print = _safe_print


class F1DataPreprocessor:
    """Clean F1 lap data by filtering non-representative laps."""

    # Track status codes from FastF1
    # '1' = Track clear, '2' = Yellow flag, '4' = SC, '6' = VSC, etc.
    VALID_TRACK_STATUS = ['1']  # Only green flag laps

    # Fuel correction per lap (seconds) - varies by circuit
    # Conservative estimate: 0.035-0.05s per lap due to fuel burn
    FUEL_CORRECTION_PER_LAP = 0.040  # seconds/lap

    def __init__(self, fuel_correction: float = FUEL_CORRECTION_PER_LAP):
        """
        Initialize preprocessor with fuel correction factor.

        Args:
            fuel_correction: Seconds gained per lap due to fuel consumption
        """
        self.fuel_correction = fuel_correction
        print(f"[OK] Preprocessor initialized (fuel correction: {fuel_correction:.3f}s/lap)")

    def filter_valid_laps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove non-representative laps from the dataset.

        Filters out:
        - In-laps and out-laps (pit entry/exit)
        - Laps under Safety Car / VSC / Yellow flags
        - Invalid lap times (NaN or extreme outliers)

        Args:
            df: Raw lap data DataFrame

        Returns:
            Filtered DataFrame with only valid race pace laps
        """
        initial_count = len(df)

        # Remove laps with missing lap times
        df_clean = df[df['LapTimeSeconds'].notna()].copy()

        # Remove in-laps (laps ending in pit entry)
        df_clean = df_clean[df_clean['PitInTime'].isna()]

        # Remove out-laps (laps starting from pit exit)
        df_clean = df_clean[df_clean['PitOutTime'].isna()]

        # Remove laps under SC/VSC/Yellow flags
        df_clean = df_clean[df_clean['TrackStatus'].isin(self.VALID_TRACK_STATUS)]

        # Remove extreme outliers (laps > 2 standard deviations from median)
        median_time = df_clean['LapTimeSeconds'].median()
        std_time = df_clean['LapTimeSeconds'].std()
        df_clean = df_clean[
            (df_clean['LapTimeSeconds'] > median_time - 2 * std_time) &
            (df_clean['LapTimeSeconds'] < median_time + 2 * std_time)
        ]

        removed = initial_count - len(df_clean)
        print(f"[OK] Filtered laps: {len(df_clean)} valid / {initial_count} total ({removed} removed)")
        print(f"  Removed: pit laps, SC/VSC laps, and outliers")

        return df_clean

    def apply_fuel_correction(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Correct lap times for fuel load reduction during the race.

        As the car burns fuel, it becomes lighter and faster. This correction
        removes that effect to isolate pure tire degradation.

        Args:
            df: Filtered lap data

        Returns:
            DataFrame with corrected lap times
        """
        df = df.copy()

        # Apply correction: add back the time gained from fuel burn
        # Earlier laps get more correction (heavier car)
        df['LapTimeCorrected'] = df['LapTimeSeconds'] + (
            df['LapNumber'] * self.fuel_correction
        )

        print(f"[OK] Applied fuel correction: +{self.fuel_correction:.3f}s per lap")

        return df

    def prepare_stint_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data for stint-based degradation analysis.

        Groups laps by driver, stint, and compound, ensuring tire life
        is properly tracked for each stint.

        Args:
            df: Corrected lap data

        Returns:
            DataFrame ready for degradation modeling
        """
        df = df.copy()

        # Ensure TyreLife is valid
        df = df[df['TyreLife'].notna()]
        df = df[df['TyreLife'] > 0]

        # Sort by driver and lap number
        df = df.sort_values(['Driver', 'LapNumber'])

        # Add stint metrics
        stint_summary = df.groupby(['Driver', 'Team', 'Stint', 'Compound']).agg({
            'TyreLife': ['min', 'max', 'count'],
            'LapTimeCorrected': ['mean', 'std']
        }).reset_index()

        print(f"\n[OK] Prepared {len(df)} laps across {len(stint_summary)} stints")
        print(f"  Compounds in data: {sorted(df['Compound'].unique())}")
        print(f"  Teams: {df['Team'].nunique()}")
        print(f"  Drivers: {df['Driver'].nunique()}")

        return df

    def process(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
        """
        Complete preprocessing pipeline.

        Args:
            df: Raw lap data from DataLoader

        Returns:
            Tuple of (processed DataFrame, metadata dict)
        """
        print("\n" + "="*60)
        print("[PREP] PREPROCESSING PIPELINE")
        print("="*60)

        # Step 1: Filter invalid laps
        df_clean = self.filter_valid_laps(df)

        # Step 2: Apply fuel correction
        df_corrected = self.apply_fuel_correction(df_clean)

        # Step 3: Prepare stint data
        df_final = self.prepare_stint_data(df_corrected)

        # Generate metadata
        metadata = {
            'total_laps_raw': len(df),
            'total_laps_processed': len(df_final),
            'removal_rate': (len(df) - len(df_final)) / len(df),
            'fuel_correction': self.fuel_correction,
            'compounds': sorted(df_final['Compound'].unique()),
            'teams': sorted(df_final['Team'].unique()),
            'drivers': sorted(df_final['Driver'].unique()),
            'stints': len(df_final.groupby(['Driver', 'Stint']))
        }

        print(f"\n[OK] Preprocessing complete!")
        print(f"  Data reduction: {metadata['removal_rate']*100:.1f}%")
        print("="*60 + "\n")

        return df_final, metadata
