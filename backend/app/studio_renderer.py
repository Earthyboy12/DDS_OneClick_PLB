import io
import json
import math
from datetime import date
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.font_manager import FontProperties
import numpy as np
import pandas as pd

from app.config import get_thai_font_path
from app.population import population_manager
from app.reference_db import get_provinces_list
from app.district_crosswalk import get_district_info

# GraphPad Prism Publication Palettes
PALETTE_LIGHT = {
    "bg": "#ffffff",
    "card_bg": "#f8fafc",
    "text": "#000000",
    "text_muted": "#334155",
    "axis": "#000000",
    "navy": "#1B365D",       # Prism Publication Navy
    "teal": "#008080",       # Prism Publication Teal
    "teal_light": "#b2dfdb",
    "blue": "#0072B2",       # Prism Cobalt Blue
    "blue_light": "#cfe8f3",
    "amber": "#E69F00",      # Prism Okabe-Ito Orange
    "rose": "#D55E00",       # Prism Vermilion / Crimson
    "crimson": "#C00000",    # Prism Classic Red
    "grey": "#7F7F7F",       # Prism Neutral Grey
    "grid": "#d1d5db",
}

PALETTE_DARK = {
    "bg": "#0b1329",
    "card_bg": "#111c38",
    "text": "#ffffff",
    "text_muted": "#cbd5e1",
    "axis": "#ffffff",
    "navy": "#38bdf8",
    "teal": "#2dd4bf",
    "teal_light": "#134e4a",
    "blue": "#60a5fa",
    "blue_light": "#0369a1",
    "amber": "#fbbf24",
    "rose": "#fb7185",
    "crimson": "#f43f5e",
    "grey": "#94a3b8",
    "grid": "#334155",
}


def get_font_props(size: int = 14, weight: str = "normal") -> FontProperties:
    font_path = get_thai_font_path()
    if font_path:
        return FontProperties(fname=font_path, size=size, weight=weight)
    return FontProperties(family=["sans-serif"], size=size, weight=weight)


def apply_prism_axes_style(
    ax: plt.Axes,
    colors: Dict[str, str],
    font_tick: FontProperties,
    show_grid: bool = False,
) -> None:
    """
    Applies authentic GraphPad Prism publication styling to a Matplotlib Axes:
    - Open top and right spines (L-shaped axis frame)
    - Thick, high-contrast left and bottom spines (2.2 pt)
    - Outward-pointing tick marks (length 6.5 pt, width 2.0 pt)
    - Bold tick labels and clean white background without grid clutter
    """
    axis_col = colors.get("axis", "#000000")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(True)
    ax.spines["bottom"].set_visible(True)
    ax.spines["left"].set_color(axis_col)
    ax.spines["bottom"].set_color(axis_col)
    ax.spines["left"].set_linewidth(2.2)
    ax.spines["bottom"].set_linewidth(2.2)

    ax.tick_params(
        axis="both",
        which="major",
        direction="out",
        length=6.5,
        width=2.0,
        colors=axis_col,
        pad=5,
    )
    if show_grid:
        ax.grid(axis="y", linestyle=":", linewidth=0.9, alpha=0.45, color=colors["grid"])
    else:
        ax.grid(False)

    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_fontproperties(font_tick)
        lbl.set_color(colors["text"])


def create_base_slide(
    theme: str = "light",
    preset: str = "full_16_9",
    dpi: int = 240,
    title: str = "",
    subtitle: str = "",
    footnote: str = "",
    source_tag: Optional[str] = None,
    transparent: bool = False,
    lang: str = "th",
    axes_rect: Optional[List[float]] = None,
) -> Tuple[plt.Figure, plt.Axes, Dict[str, str], FontProperties]:
    """
    Sets up a clean, watermark-free GraphPad Prism-style slide figure at 16:9 ratio.
    At figsize=(16, 9) and dpi=240 without bbox_inches='tight':
    16 * 240 = 3840, 9 * 240 = 2160 pixels (exact 4K UHD).
    """
    colors = PALETTE_DARK if theme == "dark" else PALETTE_LIGHT
    fig = plt.figure(figsize=(16, 9), dpi=dpi)

    bg_color = "none" if transparent else colors["bg"]
    fig.patch.set_facecolor(bg_color)

    if axes_rect is None:
        if preset == "half_slide":
            axes_rect = [0.18, 0.16, 0.68, 0.67]
        else:
            axes_rect = [0.09, 0.16, 0.84, 0.67]

    ax = fig.add_axes(axes_rect)
    ax.set_facecolor(bg_color)

    font_title = get_font_props(size=22, weight="bold")
    font_sub = get_font_props(size=13, weight="bold")
    font_foot = get_font_props(size=10, weight="normal")

    fig.text(0.06, 0.94, title, fontproperties=font_title, color=colors["text"], va="top", ha="left")
    if subtitle:
        fig.text(0.06, 0.89, subtitle, fontproperties=font_sub, color=colors["text_muted"], va="top", ha="left")

    as_of = date.today().strftime("%d/%m/%Y")
    if source_tag is None:
        source_tag = "DDS Surveillance Analytics" if lang == "en" else "ระบบวิเคราะห์ข้อมูลเฝ้าระวังโรคดิจิทัล (DDS)"
    if lang == "en":
        foot_text = f"{footnote} | Source: {source_tag} (As of {as_of})" if footnote else f"Source: {source_tag} (As of {as_of})"
    else:
        foot_text = f"{footnote} | ที่มา: {source_tag} (ข้อมูล ณ วันที่ {as_of})" if footnote else f"ที่มา: {source_tag} (ข้อมูล ณ วันที่ {as_of})"

    fig.text(0.06, 0.035, foot_text, fontproperties=font_foot, color=colors["text_muted"], va="bottom", ha="left")

    return fig, ax, colors, font_title


def export_fig_to_buffer(fig: plt.Figure, fmt: str = "png", dpi: int = 240, transparent: bool = False) -> io.BytesIO:
    """
    Exports figure to PNG (exact 3840x2160 at 16x9 @ 240 DPI), SVG, or PDF without watermarks.
    """
    buf = io.BytesIO()
    save_kwargs: Dict[str, Any] = {}
    if transparent:
        save_kwargs["transparent"] = True
    else:
        save_kwargs["facecolor"] = fig.get_facecolor()

    if fmt == "svg":
        fig.savefig(buf, format="svg", **save_kwargs)
    elif fmt == "pdf":
        fig.savefig(buf, format="pdf", **save_kwargs)
    else:
        fig.savefig(buf, format="png", dpi=dpi, **save_kwargs)

    fig.clf()
    plt.close(fig)
    buf.seek(0)
    return buf


def render_figure_1_epicurve(
    df: pd.DataFrame,
    theme: str = "light",
    preset: str = "full_16_9",
    export_fmt: str = "png",
    transparent: bool = False,
    lang: str = "th",
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    footnote: Optional[str] = None,
) -> io.BytesIO:
    """Figure 1: Weekly Epidemic Curve in GraphPad Prism style with vertical dotted year dividers."""
    is_en = lang == "en"
    eff_title = title or (
        "Weekly Epidemic Curve of Reported Cases"
        if is_en
        else "แนวโน้มจำนวนผู้ป่วยรายสัปดาห์ (Epidemic Curve)"
    )
    eff_sub = subtitle or (
        "Stacked by Patient Type (IPD, OPD, Unknown) with Calendar Year Dividers"
        if is_en
        else "จำแนกตามประเภทผู้ป่วย (IPD, OPD, ไม่ระบุประเภท) พร้อมเส้นประแบ่งเขตปีปฏิทิน"
    )
    eff_foot = footnote or (
        "Aggregated by epidemiological weeks (Sun–Sat) | Vertical dotted lines denote year boundaries"
        if is_en
        else "จำแนกตามสัปดาห์ระบาดวิทยา (อาทิตย์–เสาร์) | เส้นประแนวตั้งแสดงจุดแบ่งปีระบาดวิทยา"
    )

    fig, ax, colors, _ = create_base_slide(
        theme, preset, title=eff_title, subtitle=eff_sub, footnote=eff_foot, transparent=transparent, lang=lang
    )
    font_label = get_font_props(size=13, weight="bold")
    font_tick = get_font_props(size=10, weight="bold")
    font_yr = get_font_props(size=11, weight="bold")

    if df.empty or "epi_year" not in df.columns or "epi_week" not in df.columns:
        msg = "No surveillance data available for selected filters" if is_en else "ไม่มีข้อมูลสำหรับตัวกรองที่เลือก"
        ax.text(0.5, 0.5, msg, ha="center", va="center", fontproperties=get_font_props(18, "bold"), color=colors["text_muted"])
    else:
        grouped = df.groupby(["epi_year", "epi_week", "clean_patient_type"]).size().unstack(fill_value=0)
        for col in ["IPD", "OPD", "Unknown"]:
            if col not in grouped.columns:
                grouped[col] = 0

        grouped = grouped.sort_index()
        idx_tuples = list(grouped.index)
        labels = [f"W{int(idx[1]):02d}/{int(idx[0])}" for idx in idx_tuples]
        x = np.arange(len(grouped))

        opd = grouped["OPD"].values
        unk = grouped["Unknown"].values
        ipd = grouped["IPD"].values
        totals = opd + unk + ipd

        b1 = opd
        b2 = opd + unk

        lbl_opd = "Outpatient (OPD)" if is_en else "OPD (ผู้ป่วยนอก)"
        lbl_unk = "Unknown Type" if is_en else "ไม่ระบุประเภท (Unknown)"
        lbl_ipd = "Inpatient (IPD)" if is_en else "IPD (ผู้ป่วยใน)"

        edge_col = colors["axis"]
        bar_lw = 0.7 if len(x) <= 80 else 0.35
        ax.bar(x, opd, label=lbl_opd, color=colors["blue"], edgecolor=edge_col, linewidth=bar_lw, width=0.78)
        if unk.sum() > 0:
            ax.bar(x, unk, bottom=b1, label=lbl_unk, color=colors["grey"], edgecolor=edge_col, linewidth=bar_lw, width=0.78)
        ax.bar(x, ipd, bottom=b2, label=lbl_ipd, color=colors["rose"], edgecolor=edge_col, linewidth=bar_lw, width=0.78)

        y_max = float(max(totals)) * 1.16 if len(totals) > 0 and max(totals) > 0 else 10.0
        ax.set_ylim(0, y_max)

        # Vertical dotted lines separating years + year labels at top
        year_starts: List[Tuple[int, int]] = []
        prev_yr = None
        for i, (yr_val, _wk_val) in enumerate(idx_tuples):
            yr_int = int(yr_val)
            if prev_yr is None or yr_int != prev_yr:
                year_starts.append((i, yr_int))
                if prev_yr is not None:
                    ax.axvline(
                        x=i - 0.5,
                        color=colors["axis"],
                        linestyle=":",
                        linewidth=2.0,
                        alpha=0.9,
                        zorder=5,
                    )
                prev_yr = yr_int

        for idx_pos, yr_int in year_starts:
            yr_txt = f"{yr_int}" if is_en else f"พ.ศ. {yr_int + 543} ({yr_int})"
            ax.text(
                idx_pos + 0.3,
                y_max * 0.96,
                yr_txt,
                fontproperties=font_yr,
                color=colors["text"],
                va="top",
                ha="left",
                bbox=dict(boxstyle="round,pad=0.2", facecolor=colors["bg"], edgecolor=colors["axis"], linewidth=1.0, alpha=0.9),
            )

        step = max(1, len(x) // 16)
        ax.set_xticks(x[::step])
        ax.set_xticklabels(labels[::step], fontproperties=font_tick, rotation=35, ha="right", color=colors["text"])
        ax.set_ylabel("Reported Cases (n)" if is_en else "จำนวนผู้ป่วย (ราย)", fontproperties=font_label, color=colors["text"])
        ax.set_xlabel("Epidemiological Week / Year" if is_en else "สัปดาห์และปีระบาดวิทยา", fontproperties=font_label, color=colors["text"])

        apply_prism_axes_style(ax, colors, font_tick, show_grid=False)

        leg = ax.legend(prop=font_label, loc="upper right", frameon=True, facecolor=colors["bg"], edgecolor=colors["axis"])
        leg.get_frame().set_linewidth(1.5)
        for text in leg.get_texts():
            text.set_color(colors["text"])

    return export_fig_to_buffer(fig, export_fmt, transparent=transparent)


def render_figure_2_district_bar(
    df: pd.DataFrame,
    theme: str = "light",
    preset: str = "full_16_9",
    export_fmt: str = "png",
    transparent: bool = False,
    use_illness_district: bool = False,
    lang: str = "th",
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    footnote: Optional[str] = None,
    place_level: str = "auto",
    place_metric: str = "cases",
    year: Optional[int] = None,
    sex: Optional[str] = None,
    nationality: Optional[str] = None,
    **_kwargs,
) -> io.BytesIO:
    """
    Figure 2: Choropleth Map (with quantitative Colorbar) + Ranked Horizontal Bar Graph in GraphPad Prism style.
    Supports both Province Level ('province') and District Level ('district') and both Cases ('cases') and Incidence ('rate').
    """
    is_en = lang == "en"
    addr_th = "ที่อยู่ขณะป่วย" if use_illness_district else "ที่อยู่ปัจจุบัน"
    addr_en = "Illness Address" if use_illness_district else "Residence Address"

    p_col = "illness_prov_code" if use_illness_district else "residence_prov_code"
    d_code_col = "illness_district_code" if use_illness_district else "residence_district_code"
    unique_provs = []
    if not df.empty and p_col in df.columns:
        unique_provs = [str(p).zfill(2) for p in df[p_col].dropna().unique() if str(p).isdigit() and str(p).zfill(2) != "00"]

    if place_level == "province":
        is_prov_level = True
    elif place_level == "district":
        is_prov_level = False
    else:
        is_prov_level = len(unique_provs) > 1

    is_rate = place_metric == "rate"
    level_th = "รายจังหวัด (77 จังหวัด)" if is_prov_level else "รายอำเภอ"
    level_en = "by Province (77 Provinces)" if is_prov_level else "by District"
    metric_th = "อุบัติการณ์ต่อแสนประชากร (Incidence / 100,000)" if is_rate else "จำนวนผู้ป่วยสะสม (Cases)"
    metric_en = "Incidence per 100,000 Population" if is_rate else "Cumulative Reported Cases"

    eff_title = title or (
        f"Geographic Distribution {level_en}: {metric_en}"
        if is_en
        else f"การกระจายทางภูมิศาสตร์{level_th}: {metric_th}"
    )
    eff_sub = subtitle or (
        f"Choropleth Map & Ranked Bar Graph ({addr_en})"
        if is_en
        else f"แผนที่ Choropleth พร้อมแถบสเกลสีและกราฟแท่งจัดอันดับ ({addr_th})"
    )
    eff_foot = footnote or (
        f"Matched via official codes from dds_reference.sqlite ({addr_en})"
        if is_en
        else f"อ้างอิงรหัสพื้นที่และประชากรจากฐานข้อมูล dds_reference.sqlite ({addr_th})"
    )

    fig, ax, colors, _ = create_base_slide(
        theme, preset, title=eff_title, subtitle=eff_sub, footnote=eff_foot, transparent=transparent, lang=lang,
        axes_rect=[0.50, 0.16, 0.44, 0.67] if preset != "half_slide" else [0.24, 0.16, 0.62, 0.67]
    )
    font_label = get_font_props(size=12, weight="bold")
    font_tick = get_font_props(size=10, weight="bold")

    # Determine detected years for population lookup
    yr_col = "onset_year" if "onset_year" in df.columns else "epi_year"
    det_years = sorted([int(y) for y in df[yr_col].dropna().unique() if pd.notna(y)]) if (not df.empty and yr_col in df.columns) else [2025]
    eff_yr = det_years[0] if len(det_years) == 1 else None

    # Build province population lookup
    prov_pop_map: Dict[str, int] = {}
    prov_name_map_th: Dict[str, str] = {}
    prov_name_map_en: Dict[str, str] = {}
    for pm in get_provinces_list():
        pc = pm["province_code"]
        prov_name_map_th[pc] = pm.get("province_name_th") or pm.get("name_th") or pc
        prov_name_map_en[pc] = pm.get("province_name_en") or pm.get("name_en") or pc
        dm = population_manager.resolve_denominator(year=eff_yr, prov_codes=[pc], scope_mode="provinces", detected_years=det_years)
        if dm.get("available") and dm.get("population"):
            prov_pop_map[pc] = int(dm["population"])

    # Count districts per province in GeoJSON for district population estimation if needed
    data_dir = Path(__file__).resolve().parent / "data"
    dist_counts_per_prov: Dict[str, int] = {}
    dist_geo_path = data_dir / "thailand_districts.geojson"
    if dist_geo_path.exists():
        try:
            with open(dist_geo_path, "r", encoding="utf-8") as dgf:
                d_geo_all = json.load(dgf)
            for ft in d_geo_all.get("features", []):
                ppc = str(ft.get("properties", {}).get("pro_code", "")).zfill(2)
                dist_counts_per_prov[ppc] = dist_counts_per_prov.get(ppc, 0) + 1
        except Exception:
            pass

    # Compute values per polygon code
    val_map: Dict[str, float] = {}
    if not df.empty:
        if is_prov_level:
            cnts = df[p_col].value_counts().to_dict() if p_col in df.columns else {}
            for pc_raw, cnt_val in cnts.items():
                pc_str = str(pc_raw).zfill(2) if str(pc_raw).isdigit() else str(pc_raw)
                if is_rate:
                    pp = prov_pop_map.get(pc_str, 0)
                    val_map[pc_str] = round(cnt_val / pp * 100000.0, 2) if pp > 0 else 0.0
                else:
                    val_map[pc_str] = float(cnt_val)
        else:
            cnts = df[d_code_col].value_counts().to_dict() if d_code_col in df.columns else {}
            for dc_raw, cnt_val in cnts.items():
                dc_str = str(dc_raw).zfill(4) if str(dc_raw).isdigit() else str(dc_raw)
                if is_rate:
                    ppc = dc_str[:2]
                    custom_d_pop = population_manager.district_populations.get((eff_yr or 2024, dc_str))
                    if not custom_d_pop:
                        pp = prov_pop_map.get(ppc, 0)
                        nd = max(1, dist_counts_per_prov.get(ppc, 10))
                        custom_d_pop = pp / nd if pp > 0 else 0
                    val_map[dc_str] = round(cnt_val / custom_d_pop * 100000.0, 2) if custom_d_pop > 0 else 0.0
                else:
                    val_map[dc_str] = float(cnt_val)

    # Render Choropleth Map panel + Colorbar on the left when not half_slide
    if preset != "half_slide":
        ax_map = fig.add_axes([0.04, 0.21, 0.32, 0.62])
        ax_cbar = fig.add_axes([0.06, 0.14, 0.28, 0.028])
        ax_map.set_facecolor("none" if transparent else colors["bg"])
        ax_map.set_xticks([])
        ax_map.set_yticks([])
        for sp in ax_map.spines.values():
            sp.set_visible(True)
            sp.set_color(colors["axis"])
            sp.set_linewidth(1.8)

        geo_file = data_dir / ("thailand_provinces.geojson" if is_prov_level else "thailand_districts.geojson")
        if geo_file.exists():
            try:
                with open(geo_file, "r", encoding="utf-8") as gf:
                    geo_data = json.load(gf)
                feats = geo_data.get("features", [])
                if not is_prov_level:
                    code_key = "amp_code"
                    if unique_provs:
                        feats = [f for f in feats if str(f.get("properties", {}).get("pro_code", "")).zfill(2) in unique_provs]
                        if len(unique_provs) == 1:
                            p_nm = prov_name_map_en.get(unique_provs[0], unique_provs[0]) if is_en else prov_name_map_th.get(unique_provs[0], unique_provs[0])
                            map_title = f"District Choropleth ({p_nm})" if is_en else f"แผนที่รายอำเภอ: จ.{p_nm}"
                        else:
                            p_nms = ", ".join([prov_name_map_en.get(p, p) if is_en else prov_name_map_th.get(p, p) for p in unique_provs[:3]])
                            map_title = f"Districts ({p_nms})" if is_en else f"แผนที่รายอำเภอ: {p_nms}"
                    else:
                        map_title = "National District Choropleth" if is_en else "แผนที่รายอำเภอทั่วประเทศ"
                else:
                    code_key = "pro_code"
                    if unique_provs and len(unique_provs) <= 10:
                        feats = [f for f in feats if str(f.get("properties", {}).get("pro_code", "")).zfill(2) in unique_provs]
                        p_nms = ", ".join([prov_name_map_en.get(p, p) if is_en else prov_name_map_th.get(p, p) for p in unique_provs[:3]])
                        map_title = f"Choropleth ({p_nms})" if is_en else f"แผนที่เฉพาะจังหวัด: {p_nms}"
                    else:
                        map_title = "National Choropleth (77 Provinces)" if is_en else "แผนที่ระดับจังหวัด (77 จังหวัด)"

                max_v = max(val_map.values()) if val_map and max(val_map.values()) > 0 else 1.0
                cmap = plt.cm.YlOrRd if is_rate else plt.cm.YlGnBu
                min_x, max_x, min_y, max_y = 999.0, -999.0, 999.0, -999.0

                for feat in feats:
                    props = feat.get("properties", {})
                    code_val = str(props.get(code_key, "")).zfill(2 if is_prov_level else 4)
                    v_num = float(val_map.get(code_val, 0.0))
                    norm_v = (math.sqrt(v_num / max_v) * 0.85 + 0.12) if (v_num > 0 and max_v > 0) else 0.0
                    fill_col = cmap(norm_v) if v_num > 0 else ("#1e293b" if theme == "dark" else "#f8fafc")
                    edge_col = "#000000" if theme == "light" else "#94a3b8"
                    lw_poly = 0.55 if is_prov_level or len(feats) < 40 else 0.25

                    geom = feat.get("geometry", {})
                    gtype = geom.get("type")
                    coords = geom.get("coordinates", [])
                    polys = [coords] if gtype == "Polygon" else (coords if gtype == "MultiPolygon" else [])
                    for poly in polys:
                        if not poly:
                            continue
                        ring = poly[0]
                        if len(ring) < 3:
                            continue
                        xs = [pt[0] for pt in ring]
                        ys = [pt[1] for pt in ring]
                        min_x, max_x = min(min_x, min(xs)), max(max_x, max(xs))
                        min_y, max_y = min(min_y, min(ys)), max(max_y, max(ys))
                        patch = MplPolygon(ring, closed=True, facecolor=fill_col, edgecolor=edge_col, linewidth=lw_poly)
                        ax_map.add_patch(patch)

                if min_x < max_x and min_y < max_y:
                    pad_x = (max_x - min_x) * 0.06
                    pad_y = (max_y - min_y) * 0.06
                    ax_map.set_xlim(min_x - pad_x, max_x + pad_x)
                    ax_map.set_ylim(min_y - pad_y, max_y + pad_y)
                    ax_map.set_aspect("equal", adjustable="box")
                ax_map.set_title(map_title, fontproperties=font_label, color=colors["text"], pad=8)

                # Quantitative Colorbar under the map
                sm = ScalarMappable(norm=Normalize(vmin=0, vmax=max_v), cmap=cmap)
                sm.set_array([])
                cbar = fig.colorbar(sm, cax=ax_cbar, orientation="horizontal")
                cbar.outline.set_edgecolor(colors["axis"])
                cbar.outline.set_linewidth(1.8)
                cbar.ax.tick_params(direction="out", length=5, width=1.6, colors=colors["axis"], labelsize=9)
                cbar_lbl = (
                    ("Incidence per 100,000" if is_en else "อุบัติการณ์ (ต่อแสนประชากร)")
                    if is_rate
                    else ("Reported Cases (n)" if is_en else "จำนวนผู้ป่วยสะสม (ราย)")
                )
                cbar.set_label(cbar_lbl, fontproperties=font_tick, color=colors["text"])
            except Exception:
                pass

    # Right Side: Ranked Horizontal Bar Chart (Province or District, Cases or Incidence)
    if df.empty:
        msg = "No geographic data available" if is_en else "ไม่มีข้อมูลเชิงพื้นที่"
        ax.text(0.5, 0.5, msg, ha="center", va="center", fontproperties=get_font_props(18, "bold"), color=colors["text_muted"])
    else:
        rows_bar = []
        has_pt = "clean_patient_type" in df.columns
        if is_prov_level:
            agg_spec = {
                "total_cases": (p_col, "count"),
            }
            if has_pt:
                agg_spec["ipd_cases"] = ("clean_patient_type", lambda s: (s == "IPD").sum())
                agg_spec["opd_cases"] = ("clean_patient_type", lambda s: (s == "OPD").sum())
            grp_p = df.groupby(p_col).agg(**agg_spec).reset_index()
            for _, r in grp_p.iterrows():
                pc_str = str(r[p_col]).zfill(2) if str(r[p_col]).isdigit() else str(r[p_col])
                if pc_str in ("Unknown", "00"):
                    continue
                c_tot = int(r["total_cases"])
                ipd_c = int(r["ipd_cases"]) if has_pt else 0
                opd_c = int(r["opd_cases"]) if has_pt else 0
                kn = ipd_c + opd_c
                hp = round(ipd_c / kn * 100.0, 1) if kn > 0 else 0.0
                pp = prov_pop_map.get(pc_str, 0)
                rt = round(c_tot / pp * 100000.0, 2) if pp > 0 else 0.0
                nm = prov_name_map_en.get(pc_str, pc_str) if is_en else prov_name_map_th.get(pc_str, pc_str)
                rows_bar.append({
                    "name": nm,
                    "cases": c_tot,
                    "rate": rt,
                    "hosp_pct": hp,
                    "metric_val": rt if is_rate else c_tot,
                })
        else:
            d_name_col = ("illness_district_name_en" if is_en else "illness_district_name_th") if use_illness_district else ("residence_district_name_en" if is_en else "residence_district_name_th")
            if d_name_col not in df.columns:
                d_name_col = d_code_col
            agg_spec_d = {
                "total_cases": (d_code_col, "count"),
            }
            if has_pt:
                agg_spec_d["ipd_cases"] = ("clean_patient_type", lambda s: (s == "IPD").sum())
                agg_spec_d["opd_cases"] = ("clean_patient_type", lambda s: (s == "OPD").sum())
            grp_d = df.groupby(d_code_col).agg(**agg_spec_d).reset_index()
            for _, r in grp_d.iterrows():
                dc_str = str(r[d_code_col]).zfill(4) if str(r[d_code_col]).isdigit() else str(r[d_code_col])
                c_tot = int(r["total_cases"])
                ipd_c = int(r["ipd_cases"]) if has_pt else 0
                opd_c = int(r["opd_cases"]) if has_pt else 0
                kn = ipd_c + opd_c
                hp = round(ipd_c / kn * 100.0, 1) if kn > 0 else 0.0
                rt = float(val_map.get(dc_str, 0.0)) if is_rate else 0.0

                # Dynamic resolution via reference DB / Bangkok 50 districts lookup
                eff_p_code = dc_str[:2] if len(dc_str) == 4 and dc_str.isdigit() else (unique_provs[0] if len(unique_provs) == 1 else None)
                d_info = get_district_info(dc_str, eff_p_code)
                nm = d_info["name_en"] if is_en else d_info["name_th"]
                if not nm or "ไม่มีรายชื่อเขต" in nm:
                    raw_val = str(df[df[d_code_col] == r[d_code_col]][d_name_col].iloc[0]) if d_name_col in df.columns and len(df[df[d_code_col] == r[d_code_col]]) > 0 else dc_str
                    if "ไม่มีรายชื่อเขต" not in raw_val:
                        nm = raw_val
                    else:
                        nm = f"เขต {dc_str}" if eff_p_code == "10" else f"อำเภอ {dc_str}"

                rows_bar.append({
                    "name": str(nm)[:34],
                    "cases": c_tot,
                    "rate": rt,
                    "hosp_pct": hp,
                    "metric_val": rt if is_rate else c_tot,
                })

        bar_df = pd.DataFrame(rows_bar)
        if not bar_df.empty:
            bar_df = bar_df.sort_values(by="metric_val", ascending=False).head(15)
            bar_df = bar_df.sort_values(by="metric_val", ascending=True)

            y_pos = np.arange(len(bar_df))
            names = bar_df["name"].values
            m_vals = bar_df["metric_val"].values
            cases_arr = bar_df["cases"].values
            rates_arr = bar_df["rate"].values
            hosp_pcts = bar_df["hosp_pct"].values

            bar_fill = colors["rose"] if is_rate else colors["navy"]
            bars = ax.barh(
                y_pos,
                m_vals,
                color=bar_fill,
                edgecolor=colors["axis"],
                linewidth=1.3,
                height=0.68,
            )

            max_m = float(max(m_vals)) if len(m_vals) > 0 and max(m_vals) > 0 else 1.0
            for bar, c_val, r_val, hp in zip(bars, cases_arr, rates_arr, hosp_pcts):
                w = bar.get_width()
                if is_rate:
                    txt = f"{r_val:.2f}/100k (n={c_val:,})" if is_en else f"{r_val:.2f} ต่อแสน ({c_val:,} ราย)"
                else:
                    txt = f"{c_val:,} cases (IPD {hp}%)" if is_en else f"{c_val:,} ราย (IPD {hp}%)"
                ax.text(
                    w + max_m * 0.018,
                    bar.get_y() + bar.get_height() / 2.0,
                    txt,
                    va="center",
                    ha="left",
                    fontproperties=font_tick,
                    color=colors["text"],
                )

            ax.set_yticks(y_pos)
            ax.set_yticklabels(names, fontproperties=font_tick, color=colors["text"])
            ax.set_xlabel(
                ("Incidence per 100,000 Population" if is_en else "อุบัติการณ์ (อัตราป่วยต่อแสนประชากร)")
                if is_rate
                else ("Reported Cases (n)" if is_en else "จำนวนผู้ป่วยสะสม (ราย)"),
                fontproperties=font_label,
                color=colors["text"],
            )
            ax.set_xlim(0, max_m * 1.36)
            apply_prism_axes_style(ax, colors, font_tick, show_grid=False)

    return export_fig_to_buffer(fig, export_fmt, transparent=transparent)


def render_figure_3_age_sex_nat(
    df: pd.DataFrame,
    theme: str = "light",
    preset: str = "full_16_9",
    export_fmt: str = "png",
    transparent: bool = False,
    lang: str = "th",
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    footnote: Optional[str] = None,
) -> io.BytesIO:
    """Figure 3: Age-Sex Population Pyramid Profile in GraphPad Prism style."""
    is_en = lang == "en"
    eff_title = title or (
        "Age-Sex Surveillance Pyramid of Reported Cases"
        if is_en
        else "พีระมิดผู้ป่วยตามกลุ่มอายุและเพศ (Age-Sex Surveillance Pyramid)"
    )
    eff_sub = subtitle or (
        "5-Year Age Groups Comparing Male and Female Cases"
        if is_en
        else "จำแนกตามกลุ่มอายุมาตรฐาน 5 ปี ระหว่างเพศชายและเพศหญิง"
    )
    eff_foot = footnote or (
        "Age bands <1, 1-4, 5-9 through >=80 years | Excludes records with unknown age or sex"
        if is_en
        else "กลุ่มอายุ <1, 1-4, 5-9 จนถึง ≥80 ปี | ไม่รวมผู้ป่วยที่ไม่ระบุอายุหรือเพศ"
    )

    fig, ax, colors, _ = create_base_slide(
        theme, preset, title=eff_title, subtitle=eff_sub, footnote=eff_foot, transparent=transparent, lang=lang
    )
    font_label = get_font_props(size=13, weight="bold")
    font_tick = get_font_props(size=10, weight="bold")

    from app.measures import STANDARD_AGE_BANDS

    if df.empty or "age_band" not in df.columns or "clean_sex" not in df.columns:
        msg = "No age/sex data available" if is_en else "ไม่มีข้อมูลกลุ่มอายุและเพศ"
        ax.text(0.5, 0.5, msg, ha="center", va="center", fontproperties=get_font_props(16, "bold"), color=colors["text_muted"])
    else:
        ct = df.groupby(["age_band", "clean_sex"]).size().unstack(fill_value=0)
        for s in ["ชาย", "หญิง"]:
            if s not in ct.columns:
                ct[s] = 0

        bands = [b for b in STANDARD_AGE_BANDS if b in ct.index]
        male_counts = [-ct.loc[b, "ชาย"] for b in bands]
        female_counts = [ct.loc[b, "หญิง"] for b in bands]

        y_pos = np.arange(len(bands))
        ax.barh(
            y_pos,
            male_counts,
            color=colors["navy"],
            edgecolor=colors["axis"],
            linewidth=1.2,
            height=0.72,
            label="Male" if is_en else "เพศชาย (Male)",
        )
        ax.barh(
            y_pos,
            female_counts,
            color=colors["rose"],
            edgecolor=colors["axis"],
            linewidth=1.2,
            height=0.72,
            label="Female" if is_en else "เพศหญิง (Female)",
        )

        ax.axvline(0, color=colors["axis"], linewidth=2.0)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(bands, fontproperties=font_tick, color=colors["text"])
        ax.set_ylabel("Age Group (Years)" if is_en else "กลุ่มอายุ (ปี)", fontproperties=font_label, color=colors["text"])

        x_ticks = ax.get_xticks()
        ax.set_xticks(x_ticks)
        ax.set_xticklabels([f"{abs(int(v)):,}" for v in x_ticks], fontproperties=font_tick, color=colors["text"])
        ax.set_xlabel(
            "Reported Cases (Male <-- | --> Female)" if is_en else "จำนวนผู้ป่วย (ราย: ชาย <-- | --> หญิง)",
            fontproperties=font_label,
            color=colors["text"],
        )

        apply_prism_axes_style(ax, colors, font_tick, show_grid=False)

        leg = ax.legend(prop=font_label, loc="upper right", frameon=True, facecolor=colors["bg"], edgecolor=colors["axis"])
        leg.get_frame().set_linewidth(1.5)
        for text in leg.get_texts():
            text.set_color(colors["text"])

    return export_fig_to_buffer(fig, export_fmt, transparent=transparent)


def render_figure_4_age_rates(
    age_table: List[Dict[str, Any]],
    theme: str = "light",
    preset: str = "full_16_9",
    export_fmt: str = "png",
    transparent: bool = False,
    lang: str = "th",
    scope_label: Optional[str] = None,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    footnote: Optional[str] = None,
) -> io.BytesIO:
    """Figure 4: Age-specific Notification Rates with Exact Poisson CI in GraphPad Prism style."""
    is_en = lang == "en"
    denom_note = ""
    if age_table:
        first_valid = next((r for r in age_table if r.get("age_band") != "Unknown"), age_table[0])
        denom_note = first_valid.get("denominator_note_en" if is_en else "denominator_note_th", "")

    eff_title = title or (
        "Age-Specific Case Notification Rates per 100,000 Population"
        if is_en
        else "อัตราป่วยตามกลุ่มอายุต่อประชากรแสนคน (Age-Specific Notification Rates)"
    )
    eff_sub = subtitle or (
        f"With 95% Exact Poisson Confidence Intervals ({scope_label or 'Matched Reference Population'})"
        if is_en
        else f"พร้อมช่วงความเชื่อมั่น 95% Exact Poisson CI ({scope_label or 'จับคู่ประชากรฐานตามปีและพื้นที่จริง'})"
    )
    eff_foot = footnote or denom_note or (
        "Matched by year, province, age, and sex from dds_reference.sqlite"
        if is_en
        else "จับคู่ตัวหารตามปี จังหวัด อายุ และเพศจาก dds_reference.sqlite"
    )

    fig, ax, colors, _ = create_base_slide(
        theme, preset, title=eff_title, subtitle=eff_sub, footnote=eff_foot, transparent=transparent, lang=lang
    )
    font_label = get_font_props(size=13, weight="bold")
    font_tick = get_font_props(size=10, weight="bold")

    valid_rows = [r for r in age_table if r.get("case_notification_rate") is not None and r["age_band"] != "Unknown"]

    if not valid_rows:
        msg = (
            f"Population rate unavailable: {denom_note or 'No compatible population denominator for selected scope'}"
            if is_en
            else f"ไม่สามารถคำนวณอัตราต่อประชากรได้: {denom_note or 'ไม่มีตัวหารประชากรที่ตรงกับขอบเขตที่เลือก'}"
        )
        ax.text(0.5, 0.5, msg, ha="center", va="center", fontproperties=get_font_props(14, "bold"), color=colors["text_muted"], wrap=True)
    else:
        bands = [r["age_band"] for r in valid_rows]
        rates = [r["case_notification_rate"] for r in valid_rows]
        ci_lows = [r["case_notification_rate_ci"][0] if r["case_notification_rate_ci"] else r["case_notification_rate"] for r in valid_rows]
        ci_highs = [r["case_notification_rate_ci"][1] if r["case_notification_rate_ci"] else r["case_notification_rate"] for r in valid_rows]

        x = np.arange(len(bands))
        yerr_l = np.array(rates) - np.array(ci_lows)
        yerr_u = np.array(ci_highs) - np.array(rates)
        yerr = [np.maximum(0, yerr_l), np.maximum(0, yerr_u)]

        ax.errorbar(
            x,
            rates,
            yerr=yerr,
            fmt="none",
            ecolor=colors["axis"],
            elinewidth=1.8,
            capsize=5,
            capthick=1.8,
            zorder=3,
            label="95% Exact Poisson CI",
        )
        ax.plot(
            x,
            rates,
            color=colors["navy"],
            marker="o",
            markerfacecolor=colors["rose"],
            markeredgecolor=colors["axis"],
            markeredgewidth=1.5,
            linewidth=2.6,
            markersize=8.5,
            zorder=4,
            label="Incidence / 100,000" if is_en else "อัตราป่วยต่อแสนประชากร",
        )

        ax.set_xticks(x)
        ax.set_xticklabels(bands, fontproperties=font_tick, rotation=35, ha="right", color=colors["text"])
        ax.set_ylabel("Incidence per 100,000 Population" if is_en else "อัตราป่วยต่อแสนประชากร", fontproperties=font_label, color=colors["text"])
        ax.set_xlabel("Age Group (Years)" if is_en else "กลุ่มอายุ (ปี)", fontproperties=font_label, color=colors["text"])
        ax.set_ylim(0, max(ci_highs + [1.0]) * 1.15)

        apply_prism_axes_style(ax, colors, font_tick, show_grid=False)

        leg = ax.legend(prop=font_label, loc="upper left", frameon=True, facecolor=colors["bg"], edgecolor=colors["axis"])
        leg.get_frame().set_linewidth(1.5)
        for text in leg.get_texts():
            text.set_color(colors["text"])

    return export_fig_to_buffer(fig, export_fmt, transparent=transparent)


def render_figure_5_hospitalization_prop(
    age_table: List[Dict[str, Any]],
    theme: str = "light",
    preset: str = "full_16_9",
    export_fmt: str = "png",
    transparent: bool = False,
    lang: str = "th",
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    footnote: Optional[str] = None,
) -> io.BytesIO:
    """Figure 5: Age-specific Hospitalization Proportions with Wilson CI in GraphPad Prism style."""
    is_en = lang == "en"
    eff_title = title or (
        "Age-Specific Hospitalization Proportions (%)"
        if is_en
        else "สัดส่วนการนอนโรงพยาบาลตามกลุ่มอายุ (Hospitalization Proportion %)"
    )
    eff_sub = subtitle or (
        "IPD / (IPD + OPD) × 100 with 95% Wilson Score Confidence Intervals"
        if is_en
        else "คำนวณจาก IPD / (IPD + OPD) × 100 พร้อมช่วงความเชื่อมั่น 95% Wilson Score CI"
    )
    eff_foot = footnote or (
        "Unknown patient types are excluded from the denominator and disclosed"
        if is_en
        else "ผู้ป่วยไม่ระบุประเภทถูกตัดออกจากตัวหารตามหลักระบาดวิทยา"
    )

    fig, ax, colors, _ = create_base_slide(
        theme, preset, title=eff_title, subtitle=eff_sub, footnote=eff_foot, transparent=transparent, lang=lang
    )
    font_label = get_font_props(size=13, weight="bold")
    font_tick = get_font_props(size=10, weight="bold")

    valid_rows = [r for r in age_table if r.get("hospitalization_prop") is not None and r["age_band"] != "Unknown"]

    if not valid_rows:
        msg = "No hospitalization data available" if is_en else "ไม่มีข้อมูลสัดส่วนการนอนโรงพยาบาล"
        ax.text(0.5, 0.5, msg, ha="center", va="center", fontproperties=get_font_props(16, "bold"), color=colors["text_muted"])
    else:
        bands = [r["age_band"] for r in valid_rows]
        props = [r["hospitalization_prop"] for r in valid_rows]
        ci_lows = [r["hospitalization_prop_ci"][0] if r.get("hospitalization_prop_ci") else r["hospitalization_prop"] for r in valid_rows]
        ci_highs = [r["hospitalization_prop_ci"][1] if r.get("hospitalization_prop_ci") else r["hospitalization_prop"] for r in valid_rows]

        x = np.arange(len(bands))
        ax.bar(
            x,
            props,
            color=colors["blue"],
            edgecolor=colors["axis"],
            linewidth=1.4,
            width=0.62,
            label="Hospitalization Proportion (%)" if is_en else "สัดส่วนผู้ป่วยใน IPD (%)",
        )

        yerr_l = np.array(props) - np.array(ci_lows)
        yerr_u = np.array(ci_highs) - np.array(props)
        yerr = [np.maximum(0, yerr_l), np.maximum(0, yerr_u)]
        ax.errorbar(
            x,
            props,
            yerr=yerr,
            fmt="none",
            ecolor=colors["axis"],
            elinewidth=2.0,
            capsize=5,
            capthick=1.8,
            label="95% Wilson CI",
        )

        ax.set_xticks(x)
        ax.set_xticklabels(bands, fontproperties=font_tick, rotation=35, ha="right", color=colors["text"])
        ax.set_ylabel("Hospitalization Proportion (%)" if is_en else "สัดส่วนผู้ป่วยใน (%)", fontproperties=font_label, color=colors["text"])
        ax.set_xlabel("Age Group (Years)" if is_en else "กลุ่มอายุ (ปี)", fontproperties=font_label, color=colors["text"])
        ax.set_ylim(0, max(ci_highs + [10]) * 1.15)

        apply_prism_axes_style(ax, colors, font_tick, show_grid=False)

        leg = ax.legend(prop=font_label, loc="upper right", frameon=True, facecolor=colors["bg"], edgecolor=colors["axis"])
        leg.get_frame().set_linewidth(1.5)
        for text in leg.get_texts():
            text.set_color(colors["text"])

    return export_fig_to_buffer(fig, export_fmt, transparent=transparent)


def render_figure_6_nationality_comparison(
    df: pd.DataFrame,
    theme: str = "light",
    preset: str = "full_16_9",
    export_fmt: str = "png",
    transparent: bool = False,
    lang: str = "th",
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    footnote: Optional[str] = None,
) -> io.BytesIO:
    """Figure 6: Thai vs Non-Thai Comparison Panels in GraphPad Prism style."""
    is_en = lang == "en"
    eff_title = title or (
        "Surveillance Comparison by Nationality Group (Thai vs Non-Thai)"
        if is_en
        else "การเปรียบเทียบลักษณะผู้ป่วยระหว่างสัญชาติไทยและไม่ใช่สัญชาติไทย"
    )
    eff_sub = subtitle or (
        "Reported Cases and Hospitalization Proportions Across Nationality Groups"
        if is_en
        else "เปรียบเทียบจำนวนผู้ป่วยสะสมและสัดส่วนการนอนโรงพยาบาลตามกลุ่มสัญชาติ"
    )
    eff_foot = footnote or (
        "Classified as Thai, Non-Thai, and Unknown | Age-by-nationality population denominators are not supplied"
        if is_en
        else "จำแนกกลุ่มสัญชาติเป็น Thai / Non-Thai / Unknown | ไม่มีตัวหารประชากรจำแนกตามอายุและสัญชาติในฐานอ้างอิง"
    )

    colors = PALETTE_DARK if theme == "dark" else PALETTE_LIGHT
    fig = plt.figure(figsize=(16, 9), dpi=240)
    bg_color = "none" if transparent else colors["bg"]
    fig.patch.set_facecolor(bg_color)

    font_title = get_font_props(size=22, weight="bold")
    font_sub = get_font_props(size=13, weight="bold")
    font_foot = get_font_props(size=10, weight="normal")
    font_label = get_font_props(size=12, weight="bold")
    font_tick = get_font_props(size=10, weight="bold")

    fig.text(0.06, 0.94, eff_title, fontproperties=font_title, color=colors["text"], va="top", ha="left")
    fig.text(0.06, 0.89, eff_sub, fontproperties=font_sub, color=colors["text_muted"], va="top", ha="left")
    as_of = date.today().strftime("%d/%m/%Y")
    foot_str = (
        f"{eff_foot} | Source: DDS Surveillance Analytics (As of {as_of})"
        if is_en
        else f"{eff_foot} | ที่มา: ระบบวิเคราะห์ข้อมูลเฝ้าระวังโรคดิจิทัล (ข้อมูล ณ วันที่ {as_of})"
    )
    fig.text(0.06, 0.035, foot_str, fontproperties=font_foot, color=colors["text_muted"], va="bottom", ha="left")

    ax1 = fig.add_axes([0.08, 0.17, 0.38, 0.64])
    ax2 = fig.add_axes([0.55, 0.17, 0.38, 0.64])
    ax1.set_facecolor(bg_color)
    ax2.set_facecolor(bg_color)

    if df.empty or "nationality_group" not in df.columns:
        msg = "No nationality data available" if is_en else "ไม่มีข้อมูลสัญชาติ"
        ax1.text(0.5, 0.5, msg, ha="center", va="center", fontproperties=get_font_props(16, "bold"), color=colors["text_muted"])
    else:
        nat_summary = df.groupby("nationality_group").agg(
            cases=("temp_id", "count"),
            ipd=("clean_patient_type", lambda s: (s == "IPD").sum()),
            opd=("clean_patient_type", lambda s: (s == "OPD").sum()),
        ).reindex(["Thai", "Non-Thai", "Unknown"]).fillna(0)

        groups = (
            ["Thai", "Non-Thai", "Unknown"]
            if is_en
            else ["ไทย (Thai)", "ต่างชาติ (Non-Thai)", "ไม่ระบุ (Unknown)"]
        )
        cases = nat_summary["cases"].values
        ipds = nat_summary["ipd"].values
        knowns = ipds + nat_summary["opd"].values
        hosp_props = np.where(knowns > 0, (ipds / knowns * 100.0).round(1), 0.0)

        x = np.arange(len(groups))
        max_c = max(cases) if len(cases) > 0 and max(cases) > 0 else 1
        bar_cols = [colors["navy"], colors["rose"], colors["grey"]]
        bars1 = ax1.bar(x, cases, color=bar_cols, edgecolor=colors["axis"], linewidth=1.6, width=0.52)
        for b, c in zip(bars1, cases):
            lbl_c = f"{int(c):,}" if is_en else f"{int(c):,} ราย"
            ax1.text(
                b.get_x() + b.get_width() / 2.0,
                b.get_height() + max_c * 0.025,
                lbl_c,
                ha="center",
                va="bottom",
                fontproperties=font_tick,
                color=colors["text"],
            )
        ax1.set_xticks(x)
        ax1.set_xticklabels(groups, fontproperties=font_tick, color=colors["text"], rotation=10, ha="right")
        ax1.set_ylim(0, max_c * 1.18)
        ax1.set_ylabel("Reported Cases (n)" if is_en else "จำนวนผู้ป่วย (ราย)", fontproperties=font_label, color=colors["text"])
        ax1.set_title(
            "A. Cumulative Cases by Nationality" if is_en else "A. จำนวนผู้ป่วยสะสมตามกลุ่มสัญชาติ",
            fontproperties=font_label,
            color=colors["text"],
            pad=10,
        )
        apply_prism_axes_style(ax1, colors, font_tick, show_grid=False)

        max_hp = max(hosp_props) if len(hosp_props) > 0 and max(hosp_props) > 0 else 10
        bars2 = ax2.bar(x, hosp_props, color=bar_cols, edgecolor=colors["axis"], linewidth=1.6, width=0.52)
        for b, hp in zip(bars2, hosp_props):
            ax2.text(
                b.get_x() + b.get_width() / 2.0,
                b.get_height() + max_hp * 0.025,
                f"{hp}%",
                ha="center",
                va="bottom",
                fontproperties=font_tick,
                color=colors["text"],
            )
        ax2.set_xticks(x)
        ax2.set_xticklabels(groups, fontproperties=font_tick, color=colors["text"], rotation=10, ha="right")
        ax2.set_ylim(0, max_hp * 1.2)
        ax2.set_ylabel("IPD / (IPD + OPD) (%)" if is_en else "สัดส่วนผู้ป่วยใน IPD / (IPD + OPD) (%)", fontproperties=font_label, color=colors["text"])
        ax2.set_title(
            "B. Hospitalization Proportion by Nationality" if is_en else "B. สัดส่วนการนอนโรงพยาบาลตามสัญชาติ",
            fontproperties=font_label,
            color=colors["text"],
            pad=10,
        )
        apply_prism_axes_style(ax2, colors, font_tick, show_grid=False)

    return export_fig_to_buffer(fig, export_fmt, transparent=transparent)


def render_figure_7_forecast(
    forecast_data: Dict[str, Any],
    theme: str = "light",
    preset: str = "full_16_9",
    export_fmt: str = "png",
    transparent: bool = False,
    lang: str = "th",
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    footnote: Optional[str] = None,
) -> io.BytesIO:
    """Figure 7: Observed vs OLS Forecast in GraphPad Prism style with year boundary dividers."""
    is_en = lang == "en"
    win_note = (
        forecast_data.get("training_window_note_en")
        if is_en
        else forecast_data.get("training_window_note_th")
    ) or ""

    eff_title = title or (
        "Weekly Reported Cases & Linear Regression Forecast (OLS)"
        if is_en
        else "การพยากรณ์จำนวนผู้ป่วยรายสัปดาห์ด้วยสมการถดถอยเชิงเส้น (OLS Forecast)"
    )
    eff_sub = subtitle or (
        f"{win_note} | 80% and 95% Prediction Intervals"
        if is_en
        else f"{win_note} | พร้อมช่วงคาดหมาย 80% และ 95% Prediction Intervals"
    )
    eff_foot = footnote or (
        forecast_data.get("disclosure_en" if is_en else "disclosure_th")
        or (
            "OLS weekly_cases = beta0 + beta1 * t (<= 52 complete weeks; continuous index t across New Year)"
            if is_en
            else "โมเดล OLS จากไม่เกิน 52 สัปดาห์สมบูรณ์ล่าสุด ดัชนีเวลา t ต่อเนื่องข้ามปี"
        )
    )

    fig, ax, colors, _ = create_base_slide(
        theme, preset, title=eff_title, subtitle=eff_sub, footnote=eff_foot, transparent=transparent, lang=lang
    )
    font_label = get_font_props(size=13, weight="bold")
    font_tick = get_font_props(size=10, weight="bold")

    if forecast_data.get("status") != "success":
        ax.text(
            0.5,
            0.5,
            forecast_data.get("reason", "Forecast unavailable" if is_en else "ไม่มีข้อมูลการพยากรณ์"),
            ha="center",
            va="center",
            fontproperties=get_font_props(15, "bold"),
            color=colors["text_muted"],
            wrap=True,
        )
    else:
        history = forecast_data.get("history", [])
        lag_excluded = forecast_data.get("lag_excluded", [])
        forecasts = forecast_data.get("forecasts", [])

        all_pts = history + forecasts
        t_vals = [p["t"] for p in all_pts]
        labels = [f"W{p['epi_week']:02d}/{p['epi_year']}" for p in all_pts]

        obs_x = [p["t"] for p in history]
        obs_y = [p["observed"] for p in history]
        ax.plot(
            obs_x,
            obs_y,
            color=colors["navy"],
            marker="o",
            markerfacecolor=colors["navy"],
            markeredgecolor=colors["axis"],
            markeredgewidth=1.2,
            linewidth=2.3,
            markersize=6.5,
            label="Observed (Complete Weeks)" if is_en else "จำนวนผู้ป่วยจริง (สัปดาห์สมบูรณ์)",
        )

        fit_y = [p["fitted_clipped"] for p in history]
        ax.plot(
            obs_x,
            fit_y,
            color=colors["teal"],
            linestyle="-",
            linewidth=2.4,
            label="OLS Fitted Trend" if is_en else "เส้นแนวโน้ม OLS (Fitted)",
        )

        if lag_excluded:
            lag_x = [p["t"] for p in lag_excluded]
            lag_y = [p["observed"] for p in lag_excluded]
            ax.plot(
                lag_x,
                lag_y,
                color=colors["amber"],
                marker="D",
                markeredgecolor=colors["axis"],
                markeredgewidth=1.3,
                linestyle="None",
                markersize=8.5,
                label="Excluded Lag Week(s)" if is_en else "สัปดาห์ล่าสุดที่ตัดออก (Lag)",
            )

        max_y = max(obs_y + [10])
        if forecasts and history:
            fc_x = [history[-1]["t"]] + [p["t"] for p in forecasts]
            fc_y = [history[-1]["fitted_clipped"]] + [p["fitted_clipped"] for p in forecasts]
            pi95_l = [history[-1]["fitted_clipped"]] + [max(0.0, p["pi_95_lower"]) for p in forecasts]
            pi95_u = [history[-1]["fitted_clipped"]] + [max(0.0, p["pi_95_upper"]) for p in forecasts]
            pi80_l = [history[-1]["fitted_clipped"]] + [max(0.0, p["pi_80_lower"]) for p in forecasts]
            pi80_u = [history[-1]["fitted_clipped"]] + [max(0.0, p["pi_80_upper"]) for p in forecasts]

            ax.plot(
                fc_x,
                fc_y,
                color=colors["rose"],
                linestyle="--",
                linewidth=2.6,
                marker="s",
                markeredgecolor=colors["axis"],
                markeredgewidth=1.2,
                markersize=6.5,
                label="Point Forecast" if is_en else "ค่าพยากรณ์ (Forecast)",
            )
            ax.fill_between(fc_x, pi95_l, pi95_u, color=colors["rose"], alpha=0.14, label="95% Prediction Interval")
            ax.fill_between(fc_x, pi80_l, pi80_u, color=colors["rose"], alpha=0.26, label="80% Prediction Interval")

            ax.axvline(history[-1]["t"], color=colors["axis"], linestyle=":", linewidth=1.8)
            max_y = max(obs_y + pi95_u + [10])
            cutoff_lbl = "Training Cutoff" if is_en else "จุดตัดข้อมูลฝึกสอน"
            ax.text(history[-1]["t"] + 0.25, max_y * 0.90, cutoff_lbl, fontproperties=font_tick, color=colors["rose"])

        # Vertical dotted lines at year transitions
        prev_yr = None
        for p in all_pts:
            yr_cur = int(p["epi_year"])
            if prev_yr is not None and yr_cur != prev_yr:
                ax.axvline(p["t"] - 0.5, color=colors["axis"], linestyle=":", linewidth=1.8, alpha=0.8)
            prev_yr = yr_cur

        step = max(1, len(t_vals) // 14)
        ax.set_xticks(t_vals[::step])
        ax.set_xticklabels(labels[::step], fontproperties=font_tick, rotation=30, ha="right", color=colors["text"])
        ax.set_ylabel("Weekly Reported Cases (n)" if is_en else "จำนวนผู้ป่วยรายสัปดาห์ (ราย)", fontproperties=font_label, color=colors["text"])
        ax.set_xlabel("Epidemiological Week" if is_en else "สัปดาห์ระบาดวิทยา", fontproperties=font_label, color=colors["text"])

        apply_prism_axes_style(ax, colors, font_tick, show_grid=False)

        leg = ax.legend(prop=font_label, loc="upper right", frameon=True, facecolor=colors["bg"], edgecolor=colors["axis"])
        leg.get_frame().set_linewidth(1.5)
        for text in leg.get_texts():
            text.set_color(colors["text"])

    return export_fig_to_buffer(fig, export_fmt, transparent=transparent)


def render_figure_8_seasonal_comparison(
    seasonal_data: Dict[str, Any],
    theme: str = "light",
    preset: str = "full_16_9",
    export_fmt: str = "png",
    transparent: bool = False,
    lang: str = "th",
    metric: str = "cases",
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    footnote: Optional[str] = None,
) -> io.BytesIO:
    """
    Figure 8: Seasonal Line Graph Comparing Last 2 Years vs. 5-Year Historical Median (W01–W52)
    in authentic GraphPad Prism style.
    """
    is_en = lang == "en"
    is_rate = metric == "rate" and seasonal_data.get("has_incidence", False)

    lat_lbl = seasonal_data.get("latest_label_en" if is_en else "latest_label_th") or "Latest Year"
    prv_lbl = seasonal_data.get("prev_label_en" if is_en else "prev_label_th")
    med_lbl = seasonal_data.get("median_label_en" if is_en else "median_label_th") or "5-Year Median"

    eff_title = title or (
        "Seasonal Surveillance: Last 2 Years vs. 5-Year Historical Median"
        if is_en
        else "เปรียบเทียบการระบาดรายสัปดาห์: 2 ปีล่าสุด เทียบกับค่ามัธยฐาน 5 ปีย้อนหลัง"
    )
    eff_sub = subtitle or (
        f"{lat_lbl} (Line) vs. {prv_lbl or '-'} (Line) vs. {med_lbl} (Bars, W01–W52)"
        if is_en
        else f"เปรียบเทียบ {lat_lbl} (กราฟเส้น) • {prv_lbl or '-'} (กราฟเส้น) • {med_lbl} (กราฟแท่ง สัปดาห์ที่ 1–52)"
    )
    eff_foot = footnote or (
        "5-Year Median plotted as grey bars | Recent years plotted as trend lines (W01–W52)"
        if is_en
        else "มัธยฐาน 5 ปีแสดงด้วยกราฟแท่งสีเทา | 1 และ 2 ปีย้อนหลังแสดงด้วยกราฟเส้นแนวโน้ม (สัปดาห์ที่ 1–52)"
    )

    fig, ax, colors, _ = create_base_slide(
        theme, preset, title=eff_title, subtitle=eff_sub, footnote=eff_foot, transparent=transparent, lang=lang
    )
    font_label = get_font_props(size=13, weight="bold")
    font_tick = get_font_props(size=10, weight="bold")

    weeks = seasonal_data.get("weeks", [])
    if not seasonal_data.get("available") or not weeks:
        msg = "No seasonal comparison data available" if is_en else "ไม่มีข้อมูลสำหรับการเปรียบเทียบรายปี"
        ax.text(0.5, 0.5, msg, ha="center", va="center", fontproperties=get_font_props(16, "bold"), color=colors["text_muted"])
    else:
        x_all = [int(w["epi_week"]) for w in weeks]
        med_key = "median_5yr_rate" if is_rate else "median_5yr_cases"
        prv_key = "prev_rate" if is_rate else "prev_cases"
        lat_key = "latest_rate" if is_rate else "latest_cases"

        med_y = [float(w.get(med_key) or 0.0) for w in weeks]
        med_bar_color = "#cbd5e1" if theme == "light" else "#475569"
        med_edge_color = "#94a3b8" if theme == "light" else "#64748b"
        
        # 5-year median as grey bars
        ax.bar(
            x_all,
            med_y,
            color=med_bar_color,
            edgecolor=med_edge_color,
            linewidth=0.8,
            width=0.72,
            label=f"{med_lbl} ({'แท่งสีเทา' if not is_en else 'Grey Bar'})",
            zorder=2,
            alpha=0.85,
        )

        # Previous year as blue line
        if prv_lbl:
            prv_pts = [(int(w["epi_week"]), float(w[prv_key])) for w in weeks if w.get(prv_key) is not None]
            if prv_pts:
                ax.plot(
                    [p[0] for p in prv_pts],
                    [p[1] for p in prv_pts],
                    color=colors["blue"],
                    linestyle="-",
                    linewidth=2.5,
                    marker="s",
                    markerfacecolor=colors["blue"],
                    markeredgecolor=colors["axis"],
                    markeredgewidth=1.2,
                    markersize=6.5,
                    label=prv_lbl,
                    zorder=4,
                )

        # Latest year as crimson red line
        lat_pts = [(int(w["epi_week"]), float(w[lat_key])) for w in weeks if w.get(lat_key) is not None]
        if lat_pts:
            ax.plot(
                [p[0] for p in lat_pts],
                [p[1] for p in lat_pts],
                color=colors["crimson"],
                linestyle="-",
                linewidth=2.8,
                marker="o",
                markerfacecolor=colors["crimson"],
                markeredgecolor=colors["axis"],
                markeredgewidth=1.3,
                markersize=7.5,
                label=lat_lbl,
                zorder=5,
            )

        ticks_x = list(range(1, 53, 2))
        ax.set_xticks(ticks_x)
        ax.set_xticklabels([f"W{w:02d}" for w in ticks_x], fontproperties=font_tick, color=colors["text"])
        ax.set_xlim(0.5, 52.5)
        ax.set_xlabel(
            "Epidemiological Week (W01–W52)" if is_en else "สัปดาห์ระบาดวิทยา (สัปดาห์ที่ 1–52)",
            fontproperties=font_label,
            color=colors["text"],
        )
        ax.set_ylabel(
            ("Incidence per 100,000 Population" if is_en else "อุบัติการณ์ (อัตราป่วยต่อแสนประชากร)")
            if is_rate
            else ("Reported Cases (n)" if is_en else "จำนวนผู้ป่วยรายสัปดาห์ (ราย)"),
            fontproperties=font_label,
            color=colors["text"],
        )

        apply_prism_axes_style(ax, colors, font_tick, show_grid=False)

        leg = ax.legend(prop=font_label, loc="upper right", frameon=True, facecolor=colors["bg"], edgecolor=colors["axis"])
        leg.get_frame().set_linewidth(1.5)
        for text in leg.get_texts():
            text.set_color(colors["text"])

    return export_fig_to_buffer(fig, export_fmt, transparent=transparent)


def render_slide_readable_table(
    title: str,
    subtitle: str,
    headers: List[str],
    rows: List[List[Any]],
    footnote: str = "",
    theme: str = "light",
    export_fmt: str = "png",
    lang: str = "th",
) -> io.BytesIO:
    """
    Renders a slide-readable summary table at 4K 16:9 (3840x2160 PNG) or vector SVG/PDF without watermarks.
    """
    fig, ax, colors, _ = create_base_slide(
        theme=theme,
        preset="full_16_9",
        title=title,
        subtitle=subtitle,
        footnote=footnote,
        lang=lang,
        axes_rect=[0.05, 0.12, 0.90, 0.72],
    )
    ax.axis("off")
    font_cell = get_font_props(size=10, weight="normal")
    font_hdr = get_font_props(size=11, weight="bold")

    display_rows = [[str(c) for c in r] for r in rows[:18]]
    if not display_rows:
        display_rows = [["-" for _ in headers]]

    table = ax.table(
        cellText=display_rows,
        colLabels=headers,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.scale(1.0, 1.8)

    for (row_idx, col_idx), cell in table.get_celld().items():
        cell.set_edgecolor(colors["axis"])
        cell.set_linewidth(1.0)
        if row_idx == 0:
            cell.set_facecolor(colors["navy"] if theme == "light" else "#1e293b")
            cell.get_text().set_fontproperties(font_hdr)
            cell.get_text().set_color("#ffffff")
        else:
            cell.set_facecolor(colors["bg"] if row_idx % 2 == 1 else colors["card_bg"])
            cell.get_text().set_fontproperties(font_cell)
            cell.get_text().set_color(colors["text"])

    return export_fig_to_buffer(fig, export_fmt)
