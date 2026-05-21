import json
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from core.domain.agents.agent_result import AgentResult


class DataExportService:
    """Export agent results to JSON, CSV, and other formats."""

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_timestamp_filename(self, prefix: str, ext: str) -> Path:
        """Generate timestamped filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"{prefix}_{timestamp}.{ext}"

    def export_to_json(
        self,
        data: Dict[str, Any],
        filename: Optional[str] = None,
        prefix: str = "campaign"
    ) -> Path:
        """Export data to JSON file."""
        if filename is None:
            filepath = self._get_timestamp_filename(prefix, "json")
        else:
            filepath = self.output_dir / filename

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath

    def export_to_csv(
        self,
        data: List[Dict[str, Any]],
        filename: Optional[str] = None,
        prefix: str = "campaign"
    ) -> Path:
        """Export data to CSV file."""
        if not data:
            raise ValueError("No data to export")

        if filename is None:
            filepath = self._get_timestamp_filename(prefix, "csv")
        else:
            filepath = self.output_dir / filename

        filepath.parent.mkdir(parents=True, exist_ok=True)

        flattened_data = []
        for row in data:
            flat_row = self._flatten_dict(row)
            flattened_data.append(flat_row)

        if flattened_data:
            keys = flattened_data[0].keys()
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(flattened_data)

        return filepath

    def export_agent_result(
        self,
        result: AgentResult,
        agent_name: str,
        format: str = "json"
    ) -> Path:
        """Export AgentResult to file."""
        data = {
            "agent": agent_name,
            "status": str(result.status),
            "timestamp": datetime.now().isoformat(),
            "data": result.data,
            "error": result.error,
            "execution_time_ms": result.execution_time_ms,
        }

        if format.lower() == "json":
            return self.export_to_json(data, prefix=agent_name.lower())
        elif format.lower() == "csv":
            if isinstance(result.data, list):
                return self.export_to_csv(result.data, prefix=agent_name.lower())
            else:
                return self.export_to_csv([result.data], prefix=agent_name.lower())
        else:
            raise ValueError(f"Unsupported format: {format}")

    def export_campaign_report(
        self,
        campaign_data: Dict[str, Any],
        agents_results: Dict[str, AgentResult]
    ) -> Dict[str, Path]:
        """Export complete campaign report in multiple formats."""
        report = {
            "campaign": campaign_data,
            "agents": {},
            "generated_at": datetime.now().isoformat(),
        }

        for agent_name, result in agents_results.items():
            report["agents"][agent_name] = {
                "status": str(result.status),
                "data": result.data,
                "execution_time_ms": result.execution_time_ms,
            }

        exported_files = {}

        json_path = self.export_to_json(report, "campaign_report.json")
        exported_files["json"] = json_path

        for agent_name, result in agents_results.items():
            agent_path = self.export_agent_result(result, agent_name, "json")
            exported_files[f"{agent_name}_json"] = agent_path

        return exported_files

    @staticmethod
    def _flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
        """Flatten nested dictionary for CSV export."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(DataExportService._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, json.dumps(v, ensure_ascii=False)))
            else:
                items.append((new_key, v))
        return dict(items)