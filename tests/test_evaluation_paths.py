import unittest
from pathlib import Path
import tempfile

from evaluation.evaluation import discover_case_indices, get_ground_truth_path, get_proc_path, select_case_indices


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

    def test_get_proc_path_can_read_verified_init_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = Path(tmp) / "data" / "verified"
            spreadsheet_dir = dataset_path / "spreadsheet" / "task-1"
            spreadsheet_dir.mkdir(parents=True)
            (spreadsheet_dir / "1_task-1_init.xlsx").write_bytes(b"init")

            path = get_proc_path(dataset_path, "single", "univer-cli", "task-1", 1, "inputs")

            self.assertEqual(path, spreadsheet_dir / "1_task-1_init.xlsx")

    def test_get_proc_path_can_read_legacy_initial_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = Path(tmp) / "data" / "verified"
            spreadsheet_dir = dataset_path / "spreadsheet" / "task-1"
            spreadsheet_dir.mkdir(parents=True)
            initial_path = spreadsheet_dir / "initial.xlsx"
            initial_path.write_bytes(b"init")

            path = get_proc_path(dataset_path, "single", "univer-cli", "task-1", 1, "inputs")

            self.assertEqual(path, initial_path)

    def test_discover_case_indices_uses_golden_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = Path(tmp) / "data" / "verified"
            spreadsheet_dir = dataset_path / "spreadsheet" / "task-1"
            spreadsheet_dir.mkdir(parents=True)
            (spreadsheet_dir / "1_task-1_golden.xlsx").write_bytes(b"answer")

            self.assertEqual(discover_case_indices(dataset_path, "task-1"), [1])
            self.assertEqual(
                get_ground_truth_path(dataset_path, "task-1", 1),
                spreadsheet_dir / "1_task-1_golden.xlsx",
            )

    def test_discover_case_indices_uses_legacy_golden_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = Path(tmp) / "data" / "verified"
            spreadsheet_dir = dataset_path / "spreadsheet" / "task-1"
            spreadsheet_dir.mkdir(parents=True)
            golden_path = spreadsheet_dir / "golden.xlsx"
            golden_path.write_bytes(b"answer")

            self.assertEqual(discover_case_indices(dataset_path, "task-1"), [1])
            self.assertEqual(get_ground_truth_path(dataset_path, "task-1", 1), golden_path)

    def test_select_case_indices_filters_requested_cases(self):
        self.assertEqual(select_case_indices([1, 2, 3], [1]), [1])
        self.assertEqual(select_case_indices([1, 2, 3], [3, 1]), [1, 3])


if __name__ == "__main__":
    unittest.main()
