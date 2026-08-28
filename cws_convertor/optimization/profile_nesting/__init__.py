"""Safe 1D profile nesting foundation (phases 1-8).

The frozen 0.8.12 implementation expects the Project Model 2.24/2.7 nesting
stores as direct attributes. The unified product keeps those stores inside the
lossless Project Model 2.25 extension envelope, so install the existing
non-duplicating compatibility properties before exposing the donor API.
"""
from cws_convertor.manufacturing.m18_runtime_access import install_m18_runtime_access

install_m18_runtime_access()
from .eligibility import evaluate_part, extract_demand
from .models import *
from .results import *
from .service import create_and_register_run, register_run, register_solved_run
from .snapshot import create_input_snapshot, create_run
from .units import LengthKernel, LengthKernelError, QuantizedLength
from .formula import SafeFormulaError, evaluate_formula, validate_formula
from .machine import build_machine_snapshot, evaluate_machine_capability, evaluate_machine_stock_compatibility, validate_machine_profile, validate_tool
from .stock import build_stock_snapshot, evaluate_stock_compatibility
from .reservation import ReservationConflict, release_reservation, reserve_physical_stock
from .configuration import (
    load_formulas, load_machine_profiles, load_purchase_options, load_tools,
    set_formula, set_machine_profile, set_purchase_option, set_tool,
)
from .phase2 import create_and_register_phase2_run, create_phase2_input_snapshot, prepare_phase2_context
from .legacy_reference import illustrative_legacy_v623_reference
from .objective import default_objective_configuration, evaluate_objective, objective_key, validate_objective_configuration
from .straight_solver import solve_exact_small, solve_greedy, solve_straight_cut
from .validator import validate_straight_plan
from .phase3 import solve_and_register_phase3
from .angle_geometry import *
from .angle_solver import solve_angle_cut, solve_angle_exact_small, solve_angle_greedy
from .angle_validator import validate_angle_plan
from .transition_matrix import TransitionMatrix, TransitionMatrixEntry, build_transition_matrix
from .phase4 import solve_and_register_phase4

from .ui_state import GridLayout, ProfileNestingUIState, load_ui_state, save_ui_state
from .ui_projection import *
from .bar_visualization import BarPrimitive, BarScene, build_bar_scene, scene_to_svg
from .serialization import input_snapshot_from_dict, plan_from_dict
from .phase5_job import PreparedPhase5Solve, Phase5SolveOutcome, prepare_phase5_solve, execute_phase5_solve, commit_phase5_outcome

__all__ = [name for name in globals() if not name.startswith("_")]

from .manual_planning import *

from .phase7_reporting import *
from .phase7 import *

from .postprocessor import *
from .phase8 import *
from .benchmark import *
from .command_service import *
