import unittest
from pathlib import Path
import tempfile

from evaluation.evaluation import discover_case_indices, get_proc_path


class EvaluationPathTest(unittest.TestCase):
    def test_get_proc_path_defaults_to_model_outputs(self):
        dataset_path = Path("/repo/data/sample_data_200")

        path = get_proc_path(dataset_path, "single", "univer-cli", "59196", 3, "outputs")

        self.assertEqual(
            path,
            Path("/repo/data/sample_data_200/outputs/single_univer-cli/3_59196_output.xlsx"),
        )

    def test_get_proc_path_can_read_original_inputs_for_baselines(self):
        dataset_path = Path("/repo/data/sample_data_200")

        path = get_proc_path(dataset_path, "single", "univer-cli", "59196", 3, "inputs")

        self.assertEqual(
            path,
            Path("/repo/data/sample_data_200/spreadsheet/59196/3_59196_input.xlsx"),
        )

    def test_discover_case_indices_uses_available_answer_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = Path(tmp) / "data" / "verified"
            spreadsheet_dir = dataset_path / "spreadsheet" / "task-1"
            spreadsheet_dir.mkdir(parents=True)
            (spreadsheet_dir / "1_task-1_answer.xlsx").write_bytes(b"answer")

            self.assertEqual(discover_case_indices(dataset_path, "task-1"), [1])


if __name__ == "__main__":
    unittest.main()
