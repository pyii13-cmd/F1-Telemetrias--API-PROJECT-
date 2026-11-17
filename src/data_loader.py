"""
Data Loader Module - Download and load F1 telemetry data using FastF1.
"""
import fastf1
import pandas as pd
from pathlib import Path
from typing import Optional
import logging
import sys

# DISABLE ALL LOGGING to prevent Unicode errors on Windows
logging.basicConfig(level=logging.CRITICAL, handlers=[logging.NullHandler()])
for logger_name in ['fastf1', 'fastf1.core', 'fastf1.api', 'urllib3', 'requests']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

# Override print to catch any remaining Unicode
_original_print = print
def _safe_print(*args, **kwargs):
    try:
        _original_print(*args, **kwargs)
    except Exception:
        pass
print = _safe_print


class F1DataLoader:
    """Load F1 session data and telemetry using FastF1 library."""

    def __init__(self, cache_dir: str = "./data/cache"):
        """
        Initialize the data loader with cache configuration.

        Args:
            cache_dir: Directory to store FastF1 cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(self.cache_dir))
        print(f"[OK] FastF1 cache enabled at: {self.cache_dir.absolute()}")

    def load_session(
        self,
        year: int,
        gp: str,
        session_type: str = "R"
    ) -> fastf1.core.Session:
        """
        Load a specific F1 session.

        Args:
            year: Season year (e.g., 2024)
            gp: Grand Prix name or round number
            session_type: Session type - 'R' (Race), 'Q' (Quali), 'FP1', 'FP2', 'FP3', 'S' (Sprint)

        Returns:
            Loaded FastF1 Session object
        """
        print(f"\n[>] Loading {year} {gp} - {session_type}...")
        session = fastf1.get_session(year, gp, session_type)
        session.load()
        print(f"[OK] Session loaded: {session.event['EventName']} - {session.name}")
        return session

    def extract_laps_dataframe(
        self,
        session: fastf1.core.Session,
        drivers: Optional[list] = None
    ) -> pd.DataFrame:
        """
        Extract lap data from a session into a clean DataFrame.

        Args:
            session: Loaded FastF1 session
            drivers: List of driver codes to filter (None = all drivers)

        Returns:
            DataFrame with lap times, tire info, and track status
        """
        laps = session.laps.copy().reset_index()

        if drivers:
            laps = laps[laps['Driver'].isin(drivers)]

        # Select relevant columns for degradation analysis
        df = laps[[
            'Driver', 'Team', 'LapNumber', 'LapTime', 'Stint',
            'Compound', 'TyreLife', 'TrackStatus', 'IsPersonalBest',
            'PitInTime', 'PitOutTime', 'FreshTyre'
        ]].copy()

        # Convert LapTime to seconds
        df['LapTimeSeconds'] = df['LapTime'].dt.total_seconds()

        # Add event metadata
        df['Event'] = session.event['EventName']
        df['Year'] = session.event['EventDate'].year
        df['SessionType'] = session.name

        print(f"[OK] Extracted {len(df)} laps from {df['Driver'].nunique()} drivers")
        print(f"  Compounds: {df['Compound'].unique().tolist()}")
        print(f"  Teams: {df['Team'].nunique()}")

        return df

    def get_race_data(
        self,
        year: int,
        gp: str,
        teams: Optional[list] = None
    ) -> pd.DataFrame:
        """
        Convenience method to load race data and extract laps.

        Args:
            year: Season year
            gp: Grand Prix name or round number
            teams: List of team names to filter (None = all teams)

        Returns:
            DataFrame ready for preprocessing
        """
        session = self.load_session(year, gp, "R")
        df = self.extract_laps_dataframe(session)

        if teams:
            df = df[df['Team'].isin(teams)]
            print(f"  Filtered to teams: {teams}")

        return df
