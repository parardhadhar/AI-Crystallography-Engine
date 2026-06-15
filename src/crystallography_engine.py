"""
crystallography_engine.py — LUT-backed Crystallography Engine
=============================================================
Refactored to use 'Complete_TEM_Morphology_Map.csv' (1,920 pre-computed rows)
as a fast Pandas Lookup Table (LUT) instead of computing dot products on the fly.

The CSV encodes every valid combination of:
    Zone Axis (B) × Diffraction Vector (g) × Dislocation Loop Variant
→  Visibility (g·b), Morphology (B·n), AI Classification, UI Color

Architecture:
    __init__        → Loads CSV into memory once at server startup (~200KB)
    get_classification_profile()  → New LUT lookup method (O(1) dict return)
    evaluate_defects()            → Backward-compatible API (delegates to LUT)
    solve_single_image_gb()       → Per-mask classification using LUT + SAM geometry
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class CrystallographyEngine:
    """
    Expert Materials Science Engine for S/TEM loop analysis.

    Backed by a pre-computed Lookup Table (Complete_TEM_Morphology_Map.csv)
    containing 1,920 rows covering 26 zone axes × 26 g-vectors × 10 loop variants.

    Falls back to live dot-product math for any (B, g) pair not in the CSV.
    """

    # ─── Class-Level Constants ─────────────────────────────────────────────
    FCC_CSV_FILENAME: str = "Complete_TEM_Morphology_Map.csv"
    BCC_CSV_FILENAME: str = "Complete_BCC_TEM_Morphology_Map.csv"

    # Color hex → semantic name mapping (used by api_server overlay)
    _HEX_TO_NAME: dict[str, str] = {
        "#00FFFF":   "Cyan",
        "#FF00FF":   "Pink",
        "#FFFF00":   "Yellow",
        "#00000000": "None",
    }

    # ─── Initialization: Load the Dataset ──────────────────────────────────
    def __init__(self) -> None:
        """
        Loads the CSV files into Pandas DataFrames.
        Called once at server startup; the DataFrames live in memory for the
        entire process lifetime (~400 KB — negligible compared to SAM's 2.5 GB).
        """
        fcc_csv_path = self._resolve_csv_path(self.FCC_CSV_FILENAME)
        bcc_csv_path = self._resolve_csv_path(self.BCC_CSV_FILENAME)

        self.fcc_lut_df = pd.DataFrame()
        self.fcc_lut_keys = set()
        if fcc_csv_path is not None:
            self.fcc_lut_df = pd.read_csv(fcc_csv_path)
            self.fcc_lut_df["_key"] = (
                self.fcc_lut_df["Zone_Axis_B"] + "|" + self.fcc_lut_df["Diffraction_Vector_g"]
            )
            self.fcc_lut_keys = set(self.fcc_lut_df["_key"].unique())
            print(f"[CrystallographyEngine] Loaded FCC LUT: {len(self.fcc_lut_df)} rows, "
                  f"{len(self.fcc_lut_keys)} unique (B,g) conditions.")
        else:
            print("[CrystallographyEngine] WARNING: FCC CSV not found. Falling back to live math.")

        self.bcc_lut_df = pd.DataFrame()
        self.bcc_lut_keys = set()
        if bcc_csv_path is not None:
            self.bcc_lut_df = pd.read_csv(bcc_csv_path)
            self.bcc_lut_df["_key"] = (
                self.bcc_lut_df["Zone_Axis_B"] + "|" + self.bcc_lut_df["Diffraction_Vector_g"]
            )
            self.bcc_lut_keys = set(self.bcc_lut_df["_key"].unique())
            print(f"[CrystallographyEngine] Loaded BCC LUT: {len(self.bcc_lut_df)} rows, "
                  f"{len(self.bcc_lut_keys)} unique (B,g) conditions.")
        else:
            print("[CrystallographyEngine] WARNING: BCC CSV not found. Falling back to live math.")

        # ── Legacy crystal dictionary (fallback when LUT miss occurs) ──
        self.FCC_VARIANTS: dict[str, list[dict]] = {
            "Faulted": [
                {"n": [1, 1, 1],  "b": [1, 1, 1]},
                {"n": [-1, 1, 1], "b": [-1, 1, 1]},
                {"n": [1, -1, 1], "b": [1, -1, 1]},
                {"n": [1, 1, -1], "b": [1, 1, -1]},
            ],
            "Perfect": [
                {"n": [1, 1, 0],  "b": [1, 1, 0]},
                {"n": [-1, 1, 0], "b": [-1, 1, 0]},
                {"n": [1, 0, 1],  "b": [1, 0, 1]},
                {"n": [-1, 0, 1], "b": [-1, 0, 1]},
                {"n": [0, 1, 1],  "b": [0, 1, 1]},
                {"n": [0, -1, 1], "b": [0, -1, 1]},
            ],
        }
        self.BCC_VARIANTS: dict[str, list[dict]] = {
            "1/2<111>": [
                {"n": [1, 1, 1],  "b": [1, 1, 1]},
                {"n": [-1, 1, 1], "b": [-1, 1, 1]},
                {"n": [1, -1, 1], "b": [1, -1, 1]},
                {"n": [1, 1, -1], "b": [1, 1, -1]},
            ],
            "<100>": [
                {"n": [1, 0, 0], "b": [1, 0, 0]},
                {"n": [0, 1, 0], "b": [0, 1, 0]},
                {"n": [0, 0, 1], "b": [0, 0, 1]},
            ],
        }

    # ──────────────────────────────────────────────────────────────────────
    # 1. CSV Path Resolution
    # ──────────────────────────────────────────────────────────────────────
    def _resolve_csv_path(self, filename: str) -> Path | None:
        """Search common locations for the CSV relative to this script."""
        candidates = [
            Path(__file__).parent.parent / filename,        # project root
            Path(__file__).parent / filename,               # src/
            Path.cwd() / filename,                          # cwd
        ]
        for p in candidates:
            if p.exists():
                return p
        return None

    # ──────────────────────────────────────────────────────────────────────
    # 2. The Primary Lookup Method (NEW)
    # ──────────────────────────────────────────────────────────────────────
    def get_classification_profile(
        self,
        crystal_system: str,
        zone_axis_str: str,
        g_vector_str: str,
    ) -> dict[str, dict[str, str]]:
        """
        Fast LUT lookup for a given (Zone Axis, g-vector) diffraction condition.

        Parameters
        ----------
        zone_axis_str : str
            Zone axis in CSV format, e.g. "[0, 1, 1]".
        g_vector_str : str
            Diffraction vector in CSV format, e.g. "[2, 0, 0]".

        Returns
        -------
        dict mapping Variant_Name → {
            "classification": str,   # e.g. "Cyan (Faulted Ellipse)"
            "ui_color_hex":   str,   # e.g. "#00FFFF"
            "visibility":     str,   # "Visible" or "Invisible"
            "morphology":     str,   # "Inclined Ellipse" or "Edge-On Line"
            "loop_family":    str,   # "Faulted" or "Perfect"
            "aspect_ratio":   str,   # e.g. "1:0.816" or "0.000"
        }

        Raises
        ------
        ValueError
            If the (B, g) pair is not found in the CSV — meaning it violates
            the Weiss Zone Law (B·g ≠ 0) or was never pre-computed.
        """
        # Normalize the input strings to match CSV formatting: "[h, k, l]"
        za_key = self._normalize_vector_str(zone_axis_str)
        g_key  = self._normalize_vector_str(g_vector_str)
        composite_key = f"{za_key}|{g_key}"

        is_fcc = "FCC" in str(crystal_system).upper()
        lut_df = self.fcc_lut_df if is_fcc else self.bcc_lut_df
        lut_keys = self.fcc_lut_keys if is_fcc else self.bcc_lut_keys

        if composite_key not in lut_keys:
            raise ValueError(
                f"Invalid or forbidden diffraction condition according to the Weiss Zone Law. "
                f"No pre-computed data for B={za_key}, g={g_key}."
            )

        subset = lut_df[lut_df["_key"] == composite_key]

        profile: dict[str, dict[str, str]] = {}
        for _, row in subset.iterrows():
            profile[row["Variant_Name"]] = {
                "classification": row["AI_UI_Classification"],
                "ui_color_hex":   row["UI_Color_Hex"],
                "visibility":     row["Visibility_gb"],
                "morphology":     row["Morphology"],
                "loop_family":    row["Loop_Family"],
                "aspect_ratio":   str(row["Aspect_Ratio"]),
            }

        return profile

    # ──────────────────────────────────────────────────────────────────────
    # 3. Backward-Compatible evaluate_defects() → Delegates to LUT
    # ──────────────────────────────────────────────────────────────────────
    def evaluate_defects(
        self,
        crystal_type: str,
        zone_axis_str: str,
        g_vector_str: str,
    ) -> dict[str, dict[str, str]]:
        """
        Returns the same dict format as the old dot-product implementation:
            { "Variant [h,k,l]": { visibility, morphology, classification, ui_color } }

        Tries LUT first; falls back to live math if the (B, g) pair is missing.
        """
        za_key = self._normalize_vector_str(zone_axis_str)
        g_key  = self._normalize_vector_str(g_vector_str)
        composite_key = f"{za_key}|{g_key}"

        is_fcc = "FCC" in str(crystal_type).upper()
        lut_df = self.fcc_lut_df if is_fcc else self.bcc_lut_df
        lut_keys = self.fcc_lut_keys if is_fcc else self.bcc_lut_keys

        # ── Fast path: LUT hit ──
        if composite_key in lut_keys:
            subset = lut_df[lut_df["_key"] == composite_key]
            results: dict[str, dict[str, str]] = {}

            for _, row in subset.iterrows():
                # Reconstruct variant key in the old format: "Variant [h,k,l]"
                variant_name_raw = row["Variant_Name"]  # e.g. "1/3[111]"
                # Parse the bracket portion to get b-vector components
                b_vec = self._parse_variant_to_bvec(variant_name_raw)
                old_key = f"Variant [{int(b_vec[0])},{int(b_vec[1])},{int(b_vec[2])}]"

                # Map CSV fields to old API format
                vis = row["Visibility_gb"]
                morph_csv = row["Morphology"]
                morph = "Edge-On (Line)" if morph_csv == "Edge-On Line" else "Inclined (Ellipse)"
                classification = row["AI_UI_Classification"]
                ui_color = self._HEX_TO_NAME.get(row["UI_Color_Hex"], "None")

                # Enrich classification string for the API layer
                if vis == "Invisible":
                    classification = "Background / Invisible"
                    ui_color = "None"

                results[old_key] = {
                    "visibility":     vis,
                    "morphology":     morph,
                    "classification": classification,
                    "ui_color":       ui_color,
                }
            return results

        # ── Slow path: Live dot-product math (fallback) ──
        print(f"[CrystallographyEngine] LUT MISS for B={za_key}, g={g_key}. Computing live.")
        return self._evaluate_defects_live(crystal_type, zone_axis_str, g_vector_str)

    # ──────────────────────────────────────────────────────────────────────
    # 4. solve_single_image_gb() — Per-Mask Classification
    # ──────────────────────────────────────────────────────────────────────
    #
    # HOW THE LUT DICTIONARY GETS APPLIED TO SAM OUTPUT:
    # --------------------------------------------------
    # For each SAM-segmented mask, the api_server measures:
    #   - bounding box width/height → aspect_ratio
    #   - fitEllipse → ellipse_ratio
    #   - circularity (4π·A / P²)
    #
    # The engine then:
    #   1. Queries the LUT for all variants visible under (B, g)
    #   2. Determines if the SAM mask is empirically "Edge-On" (aspect < 0.40)
    #   3. If Edge-On: assigns 'Yellow (Edge-On)' from the LUT
    #      If Inclined: assigns 'Cyan (Faulted Ellipse)' or 'Pink (Perfect Ellipse)'
    #   4. Returns the classification string + color to api_server for overlay painting
    #
    def solve_single_mask(
        self,
        g_vector_str: str,
        material_type: str,
        zone_axis_str: str,
        box_width: float,
        box_height: float,
        image_rotation_deg: float = 0.0,
        loop_angle_deg: float = 0.0,
    ) -> dict[str, str]:
        """
        Classifies a single SAM-detected loop using LUT + empirical shape analysis.
        Uses 2D projected angle to disambiguate when multiple families share the same morphology.

        Returns a dictionary:
            {"classification": "1/3<111> Faulted Loop (Edge-On)", "ui_color": "Yellow"}
        """
        material_type = str(material_type).upper().strip()

        # Empirical morphology from SAM bounding box
        w, h = float(box_width), float(box_height)
        if max(w, h) == 0:
            return {"classification": "Invalid Shape", "ui_color": "None"}
        aspect_ratio = min(w, h) / max(w, h)
        is_empirical_edge_on = aspect_ratio < 0.40

        # ── Try LUT first ──
        za_key = self._normalize_vector_str(zone_axis_str)
        g_key  = self._normalize_vector_str(g_vector_str)
        composite_key = f"{za_key}|{g_key}"

        is_fcc = "FCC" in material_type
        lut_df = self.fcc_lut_df if is_fcc else self.bcc_lut_df
        lut_keys = self.fcc_lut_keys if is_fcc else self.bcc_lut_keys

        if composite_key in lut_keys:
            subset = lut_df[lut_df["_key"] == composite_key]
            visible = subset[subset["Visibility_gb"] == "Visible"]

            if visible.empty:
                return {"classification": "Unknown Physical Loop", "ui_color": "None"}

            if is_empirical_edge_on:
                target_rows = visible[visible["Morphology"] == "Edge-On Line"]
                morph_str = "Edge-On"
            else:
                target_rows = visible[visible["Morphology"] == "Inclined Ellipse"]
                morph_str = "Inclined"

            if target_rows.empty:
                # SAM thinks edge-on but no theoretical edge-on (or vice versa) → fallback to all visible
                target_rows = visible

            # Disambiguate ties using 2D projected angle vs SAM contour angle
            best_error = 999.0
            best_row = target_rows.iloc[0]
            
            B = self._parse_vector(zone_axis_str)
            e_x, e_y = self._get_image_basis(B)
            theta_rot = np.radians(image_rotation_deg)
            c, s = np.cos(theta_rot), np.sin(theta_rot)
            rot_matrix = np.array(((c, -s), (s, c)))

            for _, row in target_rows.iterrows():
                b_vec = self._parse_variant_to_bvec(row["Variant_Name"])
                n = b_vec  # Assuming n || b for prismatic/faulted loops
                x_comp = np.dot(n, e_x)
                y_comp = np.dot(n, e_y)
                rot_n = np.dot(rot_matrix, np.array([x_comp, y_comp]))
                theory_angle = np.degrees(np.arctan2(rot_n[1], rot_n[0]))
                
                diff = abs((theory_angle % 180) - (loop_angle_deg % 180))
                error = min(diff, 180 - diff)
                if error < best_error:
                    best_error = error
                    best_row = row
            
            color_hex = best_row["UI_Color_Hex"]
            color_name = self._HEX_TO_NAME.get(color_hex, "Cyan")

            return {
                "classification": f"{self._family_to_label(best_row['Loop_Family'], material_type)} ({morph_str})",
                "ui_color": color_name
            }

        # ── Fallback: live dot-product math ──
        return self._solve_single_live(
            g_vector_str, material_type, zone_axis_str,
            box_width, box_height, image_rotation_deg, loop_angle_deg,
        )

    # ──────────────────────────────────────────────────────────────────────
    # 5. evaluate_micrograph() — Rotated g-vector projection
    # ──────────────────────────────────────────────────────────────────────
    def evaluate_micrograph(
        self,
        zone_axis: str,
        g_vector: str,
        crystal_system: str = "FCC",
        image_rotation_deg: float = 0,
    ) -> dict[str, Any]:
        """Rotates the math, not the image. Calculates the 2D projected g-vector angle."""
        za = self._parse_vector(zone_axis)
        g = self._parse_vector(g_vector)

        e_x, e_y = self._get_image_basis(za)

        x_comp = np.dot(g, e_x)
        y_comp = np.dot(g, e_y)
        proj_2d = np.array([x_comp, y_comp])

        theta = np.radians(image_rotation_deg)
        c, s = np.cos(theta), np.sin(theta)
        rotation_matrix = np.array(((c, -s), (s, c)))

        rotated_proj = np.dot(rotation_matrix, proj_2d)
        angle = np.degrees(np.arctan2(rotated_proj[1], rotated_proj[0]))
        return {"g_angle": angle, "rotated_vector": rotated_proj}

    def theoretical_g_angle(self, g: str, z: str) -> float:
        """Backward compatibility stub."""
        return 0.0

    # ══════════════════════════════════════════════════════════════════════
    #  PRIVATE HELPERS
    # ══════════════════════════════════════════════════════════════════════

    def _normalize_vector_str(self, vec_str: str) -> str:
        """
        Normalizes any vector string format into CSV-matching "[h, k, l]".
        Handles: "[1,0,0]", "011", "[0, 1, 1]", "(1 -1 0)", etc.
        """
        v = self._parse_vector(vec_str)
        return f"[{int(v[0])}, {int(v[1])}, {int(v[2])}]"

    def _parse_vector(self, vec_str: str) -> np.ndarray:
        """Parses string '[1,1,-1]' or '011' into a NumPy array."""
        vec_str = str(vec_str).strip()
        if not vec_str.startswith("["):
            if len(vec_str) == 3 and vec_str.isdigit():
                vec_str = f"[{vec_str[0]},{vec_str[1]},{vec_str[2]}]"
            else:
                parts = vec_str.replace(",", " ").split()
                vec_str = f"[{','.join(parts)}]"
        clean = vec_str.replace("(", "[").replace(")", "]")
        try:
            return np.array(ast.literal_eval(clean), dtype=float)
        except Exception:
            return np.array([1, 0, 0], dtype=float)

    def _parse_variant_to_bvec(self, variant_name: str) -> np.ndarray:
        """
        Extracts the b-vector from a variant name like '1/3[111]' or '1/2[-110]'.
        """
        import re
        match = re.search(r"\[(-?\d),?\s*(-?\d),?\s*(-?\d)\]", variant_name)
        if match:
            return np.array([int(match.group(1)), int(match.group(2)), int(match.group(3))], dtype=float)
        # Fallback: try bracket-less format like "1/3 111"
        match = re.search(r"(-?\d)(-?\d)(-?\d)", variant_name)
        if match:
            return np.array([int(match.group(1)), int(match.group(2)), int(match.group(3))], dtype=float)
        return np.array([0, 0, 0], dtype=float)

    def _family_to_label(self, family: str, material_type: str) -> str:
        """Converts a Loop_Family string to a human-readable defect label."""
        mat = material_type.upper()
        if "FCC" in mat:
            if family == "Faulted":
                return "1/3<111> Faulted Loop"
            elif family == "Perfect":
                return "1/2<110> Perfect Loop"
        else:
            if family == "Faulted":
                return "1/2<111> Loop"
            elif family == "Perfect":
                return "<100> Loop"
        return f"{family} Loop"

    def _get_image_basis(self, za: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Returns orthonormal (e_x, e_y) basis vectors in the image plane."""
        za = za / (np.linalg.norm(za) + 1e-12)
        preferred_x = [
            np.array([1, 0, 0], dtype=float),
            np.array([1, -1, 0], dtype=float),
            np.array([0, 1, 0], dtype=float),
        ]
        e_x = None
        for p_x in preferred_x:
            proj = p_x - np.dot(p_x, za) * za
            norm = np.linalg.norm(proj)
            if norm > 1e-3:
                e_x = proj / norm
                break
        e_y = np.cross(e_x, za)
        e_y = e_y / (np.linalg.norm(e_y) + 1e-12)
        return e_x, e_y

    # ──────────────────────────────────────────────────────────────────────
    # Fallback: Live Dot-Product Math (for LUT misses)
    # ──────────────────────────────────────────────────────────────────────
    def _evaluate_defects_live(
        self,
        crystal_type: str,
        zone_axis_str: str,
        g_vector_str: str,
    ) -> dict[str, dict[str, str]]:
        """Original dot-product implementation for (B, g) pairs not in CSV."""
        crystal_type = crystal_type.upper().strip()
        dictionary = self.FCC_VARIANTS if "FCC" in crystal_type else self.BCC_VARIANTS

        B = self._parse_vector(zone_axis_str)
        g = self._parse_vector(g_vector_str)
        B_norm = np.linalg.norm(B)

        results: dict[str, dict[str, str]] = {}

        for category, variants in dictionary.items():
            for var in variants:
                n = np.array(var["n"], dtype=float)
                b = np.array(var["b"], dtype=float)
                variant_name = f"Variant [{int(b[0])},{int(b[1])},{int(b[2])}]"

                g_dot_b = np.dot(g, b)
                visibility = "Invisible" if np.isclose(g_dot_b, 0, atol=1e-6) else "Visible"

                n_norm = np.linalg.norm(n)
                cos_theta = np.dot(B, n) / (B_norm * n_norm) if (B_norm > 0 and n_norm > 0) else 1.0
                morphology = "Edge-On (Line)" if np.isclose(cos_theta, 0, atol=1e-6) else "Inclined (Ellipse)"

                if visibility == "Invisible":
                    classification = "Background / Invisible"
                    ui_color = "None"
                else:
                    if category == "Faulted":
                        base = "1/3<111> Faulted Loop"
                        ui_color = "Cyan"
                    elif category == "Perfect":
                        base = "1/2<110> Perfect Loop"
                        ui_color = "Pink"
                    elif category == "1/2<111>":
                        base = "1/2<111> Loop"
                        ui_color = "Cyan"
                    elif category == "<100>":
                        base = "<100> Loop"
                        ui_color = "Pink"
                    else:
                        base = f"{category} Loop"
                        ui_color = "Cyan"

                    if morphology == "Edge-On (Line)":
                        classification = f"{base} (Edge-On)"
                        ui_color = "Yellow"
                    else:
                        classification = base

                results[variant_name] = {
                    "visibility": visibility,
                    "morphology": morphology,
                    "classification": classification,
                    "ui_color": ui_color,
                }
        return results

    def _solve_single_mask(
        self,
        g_vector_str: str,
        material_type: str,
        zone_axis_str: str,
        box_width: float,
        box_height: float,
        image_rotation_deg: float = 0.0,
        loop_angle_deg: float = 0.0,
    ) -> dict[str, str]:
        """Fallback live classification for a single mask when LUT misses."""
        material_type = str(material_type).upper().strip()
        dictionary = self.FCC_VARIANTS if "FCC" in material_type else self.BCC_VARIANTS

        B = self._parse_vector(zone_axis_str)
        g = self._parse_vector(g_vector_str)
        B_norm = np.linalg.norm(B)

        w, h = float(box_width), float(box_height)
        if max(w, h) == 0:
            return {"classification": "Invalid Shape", "ui_color": "None"}
        aspect_ratio = min(w, h) / max(w, h)
        is_empirical_edge_on = aspect_ratio < 0.40

        visible_variants = []
        for category, variants in dictionary.items():
            for var in variants:
                n = np.array(var["n"], dtype=float)
                b = np.array(var["b"], dtype=float)
                if np.isclose(np.dot(g, b), 0, atol=1e-6):
                    continue
                n_norm = np.linalg.norm(n)
                cos_theta = np.dot(B, n) / (B_norm * n_norm) if (B_norm > 0 and n_norm > 0) else 1.0
                is_theoretical_edge_on = np.isclose(cos_theta, 0, atol=1e-6)
                e_x, e_y = self._get_image_basis(B)
                x_comp = np.dot(n, e_x)
                y_comp = np.dot(n, e_y)
                theta_rot = np.radians(image_rotation_deg)
                c, s = np.cos(theta_rot), np.sin(theta_rot)
                rot_n = np.dot(np.array(((c, -s), (s, c))), np.array([x_comp, y_comp]))
                theoretical_angle_deg = np.degrees(np.arctan2(rot_n[1], rot_n[0]))
                visible_variants.append({
                    "family": category,
                    "theory_edge_on": is_theoretical_edge_on,
                    "theory_angle": theoretical_angle_deg,
                })

        if not visible_variants:
            return {"classification": "Unknown Physical Loop", "ui_color": "None"}

        visible_families = set(v["family"] for v in visible_variants)
        if len(visible_families) == 1:
            best_family = list(visible_families)[0]
        else:
            morph_matches = [v for v in visible_variants if v["theory_edge_on"] == is_empirical_edge_on]
            if morph_matches:
                if is_empirical_edge_on:
                    best_match, best_error = None, 999.0
                    for v in morph_matches:
                        diff = abs((v["theory_angle"] % 180) - (loop_angle_deg % 180))
                        error = min(diff, 180 - diff)
                        if error < best_error:
                            best_error = error
                            best_match = v["family"]
                    best_family = best_match or "Ambiguous (Perfect/Faulted)"
                else:
                    families = [v["family"] for v in morph_matches]
                    best_family = max(set(families), key=families.count)
            else:
                best_family = "Ambiguous (Perfect/Faulted)"

        if "FCC" in material_type:
            base = "1/3<111> Faulted Loop" if best_family == "Faulted" else "1/2<110> Perfect Loop"
        else:
            base = f"{best_family} Loop" if best_family != "Ambiguous (Perfect/Faulted)" else best_family

        morph_str = "Edge-On" if is_empirical_edge_on else "Inclined"
        return f"{base} ({morph_str})"


# ══════════════════════════════════════════════════════════════════════════
#  TEST EXECUTION BLOCK
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    engine = CrystallographyEngine()

    # ── Test 1: get_classification_profile (the NEW LUT method) ──
    print("\n" + "=" * 70)
    print("  TEST: get_classification_profile('FCC', '[0, 1, 1]', '[2, 0, 0]')")
    print("=" * 70)

    try:
        profile = engine.get_classification_profile("FCC", "[0, 1, 1]", "[2, 0, 0]")
        for variant, data in profile.items():
            print(f"  {variant:15s}  ->  {data['classification']:30s}  "
                  f"Color: {data['ui_color_hex']}  "
                  f"Morph: {data['morphology']}")
    except ValueError as e:
        print(f"  ERROR: {e}")

    # ── Test 2: BCC get_classification_profile ──
    print("\n" + "=" * 70)
    print("  TEST: get_classification_profile('BCC', '[0, 1, 1]', '[2, 0, 0]')")
    print("=" * 70)

    try:
        profile = engine.get_classification_profile("BCC", "[0, 1, 1]", "[2, 0, 0]")
        for variant, data in profile.items():
            print(f"  {variant:15s}  ->  {data['classification']:30s}  "
                  f"Color: {data['ui_color_hex']}  "
                  f"Morph: {data['morphology']}")
    except ValueError as e:
        print(f"  ERROR: {e}")

    # ── Test 3: Weiss Zone Law violation ──
    print("\n" + "=" * 70)
    print("  TEST: Invalid condition (should raise ValueError)")
    print("=" * 70)
    try:
        engine.get_classification_profile("FCC", "[9, 9, 9]", "[7, 7, 7]")
        print("  BUG: Should have raised ValueError!")
    except ValueError as e:
        print(f"  Correctly raised: {e}")

    # ── Test 3: Backward-compatible evaluate_defects ──
    tests = [
        ("FCC", "[0,0,1]", "[0,2,0]", "Table 1: FCC B=[001] g=g020"),
        ("FCC", "[0,1,1]", "[1,1,-1]", "Table 2: FCC B=[011] g=g_111bar"),
        ("FCC", "[1,1,1]", "[2,2,0]", "Table 3: FCC B=[111] g=g220"),
        ("BCC", "[0,0,1]", "[1,1,0]", "BCC B=[001] g=[110]"),
    ]

    for crystal, za, gv, label in tests:
        print(f"\n{'=' * 70}")
        print(f"  {label}")
        print(f"  Crystal={crystal}  B={za}  g={gv}")
        print(f"{'=' * 70}")
        results = engine.evaluate_defects(crystal, za, gv)
        for name, data in results.items():
            if data["ui_color"] != "None":
                morph_tag = " [EDGE-ON]" if "Edge-On" in data["morphology"] else ""
                print(f"  {data['ui_color']:6s}  {name:20s}  {data['classification']}{morph_tag}")
            else:
                print(f"  INVIS   {name:20s}  {data['classification']}")
