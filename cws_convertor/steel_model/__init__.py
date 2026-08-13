"""SteelConverter cross-module contracts.

This package intentionally has no eager imports. Project Model imports only the
central tolerance policy, while the SteelModel adapter imports Project Model.
Keeping the facade empty makes that dependency direction explicit and preserves
the project's lightweight import contract.
"""
