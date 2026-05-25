import os
import time
import pandas as pd
from datetime import datetime

class DataLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"session_{self.session_id}.csv")
        self.reaction_file = os.path.join(self.log_dir, f"reactions_{self.session_id}.csv")
        self.questionnaire_file = os.path.join(self.log_dir, f"questionnaires_{self.session_id}.csv")
        self.participant_file = os.path.join(self.log_dir, f"participant_{self.session_id}.csv")
        self.report_file = os.path.join(self.log_dir, f"report_{self.session_id}.txt")
        self.participant_id = "UNKNOWN"
        
        # Buffer for periodic logging
        self.frame_data = []
        self.reaction_data = []
        self.questionnaire_data = []
        self.participant_data = {}
        
        # Session stats
        self.total_reactions = 0
        self.reaction_times = []
        self.correct_reactions = 0
        self.false_alarms = 0
        
        # State tracking for reaction logic
        self.critical_start_time = None
        self.active_critical_alert = False

    def set_participant_id(self, participant_id: str):
        self.participant_id = participant_id or "UNKNOWN"
        for row in self.frame_data + self.reaction_data + self.questionnaire_data:
            row["participant_id"] = self.participant_id
        if self.participant_data:
            self.participant_data["participant_id"] = self.participant_id

    def log_frame(self, frame_num, alert_level, min_depth, condition: str = "",
                  trial_id: str = ""):
        """Called every N frames to log the state"""
        timestamp = time.time()
        self.frame_data.append({
            "participant_id": self.participant_id,
            "timestamp": timestamp,
            "condition": condition,
            "trial_id": trial_id,
            "frame": frame_num,
            "alert_level": alert_level,
            "min_depth": min_depth
        })
        
        # Track when critical alerts start for reaction time calculation
        if alert_level == "CRITICAL" and not self.active_critical_alert:
            self.active_critical_alert = True
            self.critical_start_time = timestamp
        elif alert_level != "CRITICAL":
            self.active_critical_alert = False
            self.critical_start_time = None
            
    def log_reaction(self, frame_num, alert_level, trial: dict | None = None,
                     trial_start_time: float | None = None,
                     condition: str = "", response_source: str = "desktop",
                     network_latency_ms: float = 0):
        """
        Called when user presses BRAKE.

        If `trial` is provided (playlist mode), score against the trial's
        expected_alert_level and event_start_ms reaction window:
            - SAFE trial → false alarm
            - CRITICAL/WARNING + brake within [event_start_ms-1000, event_start_ms+3000] → hit
            - CRITICAL/WARNING + brake outside window → counted but flagged
        """
        timestamp = time.time()
        self.total_reactions += 1

        reaction_time_ms = 0
        is_correct = False
        outcome = "unknown"
        trial_id = trial["id"] if trial else None

        if trial is not None:
            expected = trial.get("expected_alert_level", "SAFE")
            event_start_ms = int(trial.get("event_start_ms", 0))
            t_into_clip_ms = int((timestamp - trial_start_time) * 1000) if trial_start_time else 0
            already_pressed = any(
                row.get("trial_id") == trial_id and row.get("frame", -1) >= 0
                for row in self.reaction_data
            )

            if already_pressed:
                outcome = "duplicate_press"
            elif expected == "SAFE":
                outcome = "false_alarm"
                self.false_alarms += 1
            else:
                # CRITICAL or WARNING — check the reaction window
                window_start = event_start_ms - 1000
                window_end = event_start_ms + 3000
                if window_start <= t_into_clip_ms <= window_end:
                    outcome = "hit"
                    is_correct = True
                    self.correct_reactions += 1
                    reaction_time_ms = max(0, t_into_clip_ms - event_start_ms)
                    self.reaction_times.append(reaction_time_ms)
                else:
                    outcome = "out_of_window"
                    # Out-of-window press is neither hit nor false alarm — log it but don't count

            self.reaction_data.append({
                "participant_id": self.participant_id,
                "timestamp": timestamp,
                "condition": condition,
                "trial_id": trial_id,
                "event_type": trial.get("event_type", ""),
                "expected_level": expected,
                "frame": frame_num,
                "alert_level_at_press": alert_level,
                "t_into_clip_ms": t_into_clip_ms,
                "event_start_ms": event_start_ms,
                "reaction_time_ms": reaction_time_ms,
                "outcome": outcome,
                "is_correct": is_correct,
                "response_source": response_source,
                "network_latency_ms": network_latency_ms,
            })
        else:
            # Free-play (single video) — old behavior
            if alert_level in ("CRITICAL", "WARNING"):
                is_correct = True
                self.correct_reactions += 1
                if self.critical_start_time:
                    reaction_time_ms = int((timestamp - self.critical_start_time) * 1000)
                    self.reaction_times.append(reaction_time_ms)
                outcome = "hit"
            else:
                self.false_alarms += 1
                outcome = "false_alarm"

            self.reaction_data.append({
                "participant_id": self.participant_id,
                "timestamp": timestamp,
                "condition": condition,
                "trial_id": None,
                "event_type": "",
                "expected_level": "",
                "frame": frame_num,
                "alert_level_at_press": alert_level,
                "t_into_clip_ms": 0,
                "event_start_ms": 0,
                "reaction_time_ms": reaction_time_ms,
                "outcome": outcome,
                "is_correct": is_correct,
                "response_source": response_source,
                "network_latency_ms": network_latency_ms,
            })

        return reaction_time_ms

    def log_miss(self, trial_id, event_type, expected_level, condition: str = "",
                 event_start_ms: int = 0):
        """Called when a CRITICAL/WARNING trial ends with no brake press."""
        self.reaction_data.append({
            "participant_id": self.participant_id,
            "timestamp": time.time(),
            "condition": condition,
            "trial_id": trial_id,
            "event_type": event_type,
            "expected_level": expected_level,
            "frame": -1,
            "alert_level_at_press": "",
            "t_into_clip_ms": 0,
            "event_start_ms": event_start_ms,
            "reaction_time_ms": 0,
            "outcome": "miss",
            "is_correct": False,
            "response_source": "",
            "network_latency_ms": 0,
        })

    def log_correct_rejection(self, trial_id, event_type, condition: str = ""):
        """Record a safe trial that completed without an unnecessary brake."""
        self.reaction_data.append({
            "participant_id": self.participant_id,
            "timestamp": time.time(),
            "condition": condition,
            "trial_id": trial_id,
            "event_type": event_type,
            "expected_level": "SAFE",
            "frame": -1,
            "alert_level_at_press": "",
            "t_into_clip_ms": 0,
            "event_start_ms": 0,
            "reaction_time_ms": 0,
            "outcome": "correct_rejection",
            "is_correct": True,
            "response_source": "",
            "network_latency_ms": 0,
        })

    def log_nasa_tlx(self, block_num: int, condition: str, scores: dict):
        """Store raw NASA-TLX sub-scales and the unweighted block total."""
        values = {key: int(value) for key, value in scores.items()}
        row = {
            "participant_id": self.participant_id,
            "instrument": "NASA_TLX",
            "block_num": block_num,
            "condition": condition,
            **values,
            "tlx_total": sum(values.values()),
            "tlx_mean": round(sum(values.values()) / len(values), 2),
        }
        self.questionnaire_data = [
            existing
            for existing in self.questionnaire_data
            if not (
                existing.get("instrument") == "NASA_TLX"
                and existing.get("block_num") == block_num
            )
        ]
        self.questionnaire_data.append(row)

    def log_final_questionnaire(self, sus_responses: dict, responses: dict):
        """Store final SUS, trust, usability and demographic responses."""
        sus = {key: int(value) for key, value in sus_responses.items()}
        sus_total = 0
        for index in range(1, 11):
            value = sus[f"sus_{index}"]
            sus_total += value - 1 if index % 2 else 5 - value
        self.participant_data = {
            "participant_id": self.participant_id,
            **responses,
            **sus,
            "sus_score": sus_total * 2.5,
        }
        
    def get_session_stats(self):
        avg_reaction = 0
        if self.reaction_times:
            avg_reaction = sum(self.reaction_times) / len(self.reaction_times)
            
        hits = sum(1 for row in self.reaction_data if row.get("outcome") == "hit")
        misses = sum(1 for row in self.reaction_data if row.get("outcome") == "miss")
        false_alarms = sum(1 for row in self.reaction_data if row.get("outcome") == "false_alarm")
        correct_rejections = sum(1 for row in self.reaction_data if row.get("outcome") == "correct_rejection")
        hazard_trials = hits + misses
        detection_rate = (hits / hazard_trials * 100) if hazard_trials else 0
        safe_trials = false_alarms + correct_rejections
        false_alarm_rate = (false_alarms / safe_trials * 100) if safe_trials else 0
            
        return {
            "total": self.total_reactions,
            "avg_time": int(avg_reaction),
            "correct_pct": int(detection_rate),
            "hits": hits,
            "misses": misses,
            "detection_rate": int(detection_rate),
            "false_alarms": false_alarms,
            "correct_rejections": correct_rejections,
            "false_alarm_rate": int(false_alarm_rate),
            "tlx_blocks": len(self.questionnaire_data),
            "sus_score": self.participant_data.get("sus_score"),
            "reactions": self.reaction_data
        }

    def save_session(self, participant_id="UNKNOWN"):
        """Export data and generate report"""
        if self.frame_data:
            df_frames = pd.DataFrame(self.frame_data)
            df_frames.to_csv(self.log_file, index=False)
            
        if self.reaction_data:
            df_reactions = pd.DataFrame(self.reaction_data)
            df_reactions.to_csv(self.reaction_file, index=False)

        pd.DataFrame(self.questionnaire_data).to_csv(self.questionnaire_file, index=False)
        participant_rows = [self.participant_data] if self.participant_data else []
        pd.DataFrame(participant_rows).to_csv(self.participant_file, index=False)
            
        stats = self.get_session_stats()
        
        with open(self.report_file, "w") as f:
            f.write(f"DEPTHGUARD SESSION REPORT\n")
            f.write(f"=========================\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Participant ID: {participant_id}\n\n")
            f.write(f"Total Reactions: {stats['total']}\n")
            f.write(f"Hits: {stats['hits']}\n")
            f.write(f"Misses: {stats['misses']}\n")
            f.write(f"Detection Rate: {stats['detection_rate']}%\n")
            f.write(f"False Alarms: {stats['false_alarms']} ({stats['false_alarm_rate']}%)\n")
            f.write(f"Average Reaction Time: {stats['avg_time']} ms\n\n")
            f.write(f"NASA-TLX Blocks Collected: {stats['tlx_blocks']}/3\n")
            if stats["sus_score"] is not None:
                f.write(f"SUS Score: {stats['sus_score']:.1f}\n")
            f.write("\n")
            f.write("Reaction Log:\n")
            for r in self.reaction_data:
                f.write(
                    f" Frame {r['frame']}: "
                    f"{r.get('alert_level_at_press', '')} "
                    f"({r.get('outcome', '')}) "
                    f"- Trial: {r.get('trial_id', '-')} "
                    f"- RT: {r['reaction_time_ms']}ms\n"
                )
