# Intervals.icu Integration for Home Assistant

A custom Home Assistant integration for [Intervals.icu](https://intervals.icu), a training analytics platform for endurance athletes.

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Search for "Intervals.icu" and install
3. Restart Home Assistant

### Manual

1. Copy the `custom_components/intervals_icu` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for "Intervals.icu"
3. Enter your **Athlete ID** and **API Key**
   - Find these in your Intervals.icu account under **Settings** > **Developer Settings**

## Sensors

### Wellness (daily)

| Sensor | Description |
|--------|-------------|
| Weight | Body weight (kg) |
| Resting heart rate | Resting HR (bpm) |
| HRV | Heart rate variability (ms) |
| HRV SDNN | HRV SDNN (ms) |
| Sleep time | Total sleep duration |
| Sleep score | Sleep quality score |
| Readiness | Readiness score |
| SpO2 | Blood oxygen saturation (%) |
| Steps | Daily step count |
| Fitness (CTL) | Chronic Training Load |
| Fatigue (ATL) | Acute Training Load |
| Form (TSB) | Training Stress Balance (CTL - ATL) |
| Ramp rate | Training ramp rate |
| Stress | Subjective stress level |
| Mood | Subjective mood |
| Motivation | Subjective motivation |
| Fatigue (subjective) | Subjective fatigue |
| Soreness | Subjective soreness |
| Basal calories | Basal metabolic calories |
| Active calories | Calories from activity |
| Total calories | Total daily calories |

### Latest Activity

| Sensor | Description |
|--------|-------------|
| Last activity | Activity name |
| Last activity type | Activity type (Ride, Run, etc.) |
| Last activity duration | Moving time |
| Last activity distance | Distance (m) |
| Last activity training load | Training load score |
| Last activity avg HR | Average heart rate (bpm) |
| Last activity max HR | Max heart rate (bpm) |
| Last activity avg cadence | Average cadence (rpm) |
| Last activity avg power | Average power (W) |
| Last activity normalized power | Normalized power (W) |
| Last activity intensity | Intensity factor |
| Last activity calories | Calories burned |
| Last activity elevation gain | Total elevation gain (m) |

### Planned Workouts

| Sensor | Description |
|--------|-------------|
| Next workout | Name of next planned workout |
| Next workout date | Date of next planned workout |
| Next workout type | Type of next planned workout |

### Athlete Profile

| Sensor | Description |
|--------|-------------|
| FTP | Functional Threshold Power (W) |
| LTHR | Lactate Threshold Heart Rate (bpm) |
| Max heart rate | Max heart rate (bpm) |
| Resting heart rate (profile) | Resting HR from profile (bpm) |

### Calendar

A calendar entity shows planned workouts, targets, notes, and races from your Intervals.icu calendar. Events appear in the Home Assistant calendar card and can be used in automations.

## Data Update

Data is polled from the Intervals.icu API every 2 hours. The calendar fetches events on demand when browsing date ranges.
