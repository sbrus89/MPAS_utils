#!/usr/bin/env python3
"""
Simulation Throughput Monitor

Monitors a simulation log file and calculates throughput as wall clock seconds
per simulated day by tracking simulation timestamps at regular intervals.
Optionally reads configuration to project completion time.
"""

import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import argparse


class SimulationThroughputMonitor:
    """Monitor simulation log files and calculate throughput metrics."""
    
    def __init__(self, log_file: str, check_interval: float = 60.0, 
                 config_file: Optional[str] = None):
        """
        Initialize the throughput monitor.
        
        Args:
            log_file: Path to the simulation log file
            check_interval: Time between checks in wall clock seconds
            config_file: Optional path to configuration file
        """
        self.log_file = Path(log_file)
        self.check_interval = check_interval
        self.config_file = Path(config_file) if config_file else None
        
        self.timestamp_pattern = re.compile(
            r'Doing timestep (\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2})'
        )
        self.config_duration_pattern = re.compile(
            r"config_run_duration\s*=\s*['\"](\d+)_(\d{2}):(\d{2}):(\d{2})['\"]"
        )
        
        # Store previous measurement
        self.prev_sim_time: Optional[datetime] = None
        self.prev_wall_time: Optional[float] = None
        
        # Store run duration if available
        self.run_duration: Optional[timedelta] = None
        if self.config_file:
            self.run_duration = self.parse_run_duration()
        
    def parse_simulation_time(self, timestamp_str: str) -> datetime:
        """
        Parse simulation timestamp string to datetime object.
        
        Args:
            timestamp_str: Timestamp in format YYYY-MM-DD_HH:MM:SS
            
        Returns:
            datetime object representing the simulation time
        """
        return datetime.strptime(timestamp_str, '%Y-%m-%d_%H:%M:%S')
    
    def parse_run_duration(self) -> Optional[timedelta]:
        """
        Parse the run duration from the configuration file.
        
        Returns:
            timedelta representing the total run duration, or None if not found
        """
        if not self.config_file or not self.config_file.exists():
            return None
        
        try:
            with open(self.config_file, 'r') as f:
                for line in f:
                    match = self.config_duration_pattern.search(line)
                    if match:
                        days = int(match.group(1))
                        hours = int(match.group(2))
                        minutes = int(match.group(3))
                        seconds = int(match.group(4))
                        
                        duration = timedelta(
                            days=days,
                            hours=hours,
                            minutes=minutes,
                            seconds=seconds
                        )
                        print(f"Found run duration in config: {self.format_duration(duration)}")
                        return duration
        except Exception as e:
            print(f"Error reading config file: {e}")
            return None
        
        print(f"Warning: config_run_duration not found in {self.config_file}")
        return None
    
    def format_duration(self, duration: timedelta) -> str:
        """
        Format a timedelta as DDDD_HH:MM:SS.
        
        Args:
            duration: timedelta to format
            
        Returns:
            Formatted duration string
        """
        total_seconds = int(duration.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{days:04d}_{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def get_first_simulation_time(self) -> Optional[datetime]:
        """
        Extract the first simulation timestamp from the log file.
        
        Returns:
            First simulation time, or None if no timestamps found
        """
        if not self.log_file.exists():
            return None
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    match = self.timestamp_pattern.search(line)
                    if match:
                        return self.parse_simulation_time(match.group(1))
        except Exception as e:
            print(f"Error reading log file: {e}")
            return None
        
        return None
    
    def get_latest_simulation_time(self) -> Optional[datetime]:
        """
        Extract the most recent simulation timestamp from the log file.
        
        Returns:
            Most recent simulation time, or None if no timestamps found
        """
        if not self.log_file.exists():
            return None
        
        latest_time = None
        
        try:
            with open(self.log_file, 'r') as f:
                # Read file in reverse to find most recent timestamp efficiently
                # For very large files, consider using a more sophisticated approach
                for line in f:
                    match = self.timestamp_pattern.search(line)
                    if match:
                        latest_time = self.parse_simulation_time(match.group(1))
        except Exception as e:
            print(f"Error reading log file: {e}")
            return None
        
        return latest_time
    
    def calculate_throughput(
        self, 
        current_sim_time: datetime, 
        current_wall_time: float
    ) -> Optional[float]:
        """
        Calculate throughput in wall clock seconds per simulated day.
        
        Args:
            current_sim_time: Current simulation timestamp
            current_wall_time: Current wall clock time
            
        Returns:
            Throughput in seconds/day, or None if insufficient data
        """
        if self.prev_sim_time is None or self.prev_wall_time is None:
            return None
        
        # Calculate elapsed times
        sim_elapsed = (current_sim_time - self.prev_sim_time).total_seconds()
        wall_elapsed = current_wall_time - self.prev_wall_time
        
        # Avoid division by zero
        if sim_elapsed == 0:
            return None
        
        # Calculate seconds per simulated day
        sim_days = sim_elapsed / 86400.0  # 86400 seconds in a day
        throughput = wall_elapsed / sim_days if sim_days > 0 else None
        
        return throughput
    
    def calculate_completion_projection(
        self,
        current_sim_time: datetime,
        throughput: float,
        start_time: datetime
    ) -> Optional[Tuple[timedelta, datetime, float]]:
        """
        Calculate projected time until simulation completion.
        
        Args:
            current_sim_time: Current simulation timestamp
            throughput: Current throughput in seconds/day
            start_time: Starting simulation timestamp
            
        Returns:
            Tuple of (time_remaining, completion_datetime, percent_complete)
            or None if insufficient data
        """
        if self.run_duration is None or throughput is None or throughput <= 0:
            return None
        
        # Calculate elapsed simulation time from the start
        sim_elapsed = current_sim_time - start_time
        
        # Calculate remaining simulation time
        sim_remaining = self.run_duration - sim_elapsed
        
        # Calculate percent complete based on elapsed vs total duration
        percent_complete = (sim_elapsed.total_seconds() / 
                          self.run_duration.total_seconds()) * 100.0
        
        if sim_remaining.total_seconds() <= 0:
            # Simulation should be complete
            return timedelta(0), datetime.now(), 100.0
        
        # Calculate wall clock time remaining
        sim_days_remaining = sim_remaining.total_seconds() / 86400.0
        wall_seconds_remaining = sim_days_remaining * throughput
        wall_time_remaining = timedelta(seconds=wall_seconds_remaining)
        
        # Calculate completion datetime
        completion_time = datetime.now() + wall_time_remaining
        
        return wall_time_remaining, completion_time, percent_complete
    
    def format_time_remaining(self, time_remaining: timedelta) -> str:
        """
        Format time remaining in a human-readable format.
        
        Args:
            time_remaining: timedelta representing time remaining
            
        Returns:
            Formatted string
        """
        total_seconds = int(time_remaining.total_seconds())
        
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or not parts:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        
        return ", ".join(parts)
    
    def format_throughput_report(
        self, 
        sim_time: datetime, 
        throughput: Optional[float],
        start_time: Optional[datetime] = None
    ) -> str:
        """
        Format a human-readable throughput report.
        
        Args:
            sim_time: Current simulation time
            throughput: Throughput in seconds/day
            start_time: Starting simulation time for completion projection
            
        Returns:
            Formatted report string
        """
        report = f"\n{'='*60}\n"
        report += f"Simulation Throughput Report\n"
        report += f"{'='*60}\n"
        report += f"Wall Clock Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Simulation Time: {sim_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if throughput is not None:
            report += f"Throughput: {throughput:.2f} wall seconds per simulated day\n"
            
            # Additional useful metrics
            if throughput > 0:
                sim_days_per_hour = 3600.0 / throughput
                report += f"            {sim_days_per_hour:.4f} simulated days per wall hour\n"
                
                if sim_days_per_hour > 0:
                    hours_per_sim_year = 365.25 / sim_days_per_hour
                    report += f"            {hours_per_sim_year:.2f} wall hours per simulated year\n"
            
            # Add completion projection if available
            if start_time is not None:
                projection = self.calculate_completion_projection(
                    sim_time, throughput, start_time
                )
                
                if projection is not None:
                    time_remaining, completion_time, percent_complete = projection
                    
                    report += f"\n--- Completion Projection ---\n"
                    report += f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    report += f"Run Duration: {self.format_duration(self.run_duration)}\n"
                    report += f"Progress: {percent_complete:.2f}%\n"
                    report += f"Time Remaining: {self.format_time_remaining(time_remaining)}\n"
                    report += f"Estimated Completion: {completion_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        else:
            report += "Throughput: Waiting for sufficient data...\n"
        
        report += f"{'='*60}\n"
        
        return report
    
    def monitor(self, duration: Optional[float] = None, verbose: bool = True):
        """
        Monitor the simulation log file and report throughput.
        
        Args:
            duration: Total monitoring duration in seconds (None for infinite)
            verbose: Print detailed reports
        """
        start_time = time.time()
        iteration = 0
        
        # Get the first simulation time from the log (actual start of simulation)
        first_sim_time: Optional[datetime] = None
        
        print(f"Starting simulation throughput monitor...")
        print(f"Log file: {self.log_file}")
        if self.config_file:
            print(f"Config file: {self.config_file}")
        print(f"Check interval: {self.check_interval} seconds")
        print(f"Duration: {'Infinite' if duration is None else f'{duration} seconds'}")
        print("\nMonitoring...\n")
        
        try:
            while True:
                # Check if duration exceeded
                if duration is not None and (time.time() - start_time) >= duration:
                    print("Monitoring duration completed.")
                    break
                
                # Get current measurements
                current_wall_time = time.time()
                current_sim_time = self.get_latest_simulation_time()
                
                if current_sim_time is not None:
                    # Get first simulation time on first successful read
                    if first_sim_time is None:
                        first_sim_time = self.get_first_simulation_time()
                        if first_sim_time:
                            print(f"Detected simulation start time: {first_sim_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    
                    # Calculate throughput
                    throughput = self.calculate_throughput(
                        current_sim_time, 
                        current_wall_time
                    )
                    
                    # Display report
                    if verbose:
                        report = self.format_throughput_report(
                            current_sim_time, 
                            throughput,
                            first_sim_time
                        )
                        print(report)
                    
                    # Update previous measurements
                    self.prev_sim_time = current_sim_time
                    self.prev_wall_time = current_wall_time
                else:
                    print(f"No simulation timestamps found in {self.log_file}")
                
                iteration += 1
                
                # Wait for next check
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user.")


def main():
    """Main entry point for the throughput monitor."""
    parser = argparse.ArgumentParser(
        description='Monitor simulation log file and calculate throughput'
    )
    parser.add_argument(
        'log_file',
        help='Path to the simulation log file'
    )
    parser.add_argument(
        '-i', '--interval',
        type=float,
        default=60.0,
        help='Check interval in seconds (default: 60)'
    )
    parser.add_argument(
        '-d', '--duration',
        type=float,
        default=None,
        help='Total monitoring duration in seconds (default: infinite)'
    )
    parser.add_argument(
        '-c', '--config',
        type=str,
        default=None,
        help='Path to configuration file for completion projection'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress verbose output'
    )
    
    args = parser.parse_args()
    
    monitor = SimulationThroughputMonitor(
        log_file=args.log_file,
        check_interval=args.interval,
        config_file=args.config
    )
    
    monitor.monitor(
        duration=args.duration,
        verbose=not args.quiet
    )


if __name__ == '__main__':
    main()
