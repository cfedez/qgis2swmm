# -*- coding: utf-8 -*-
"""
QGIS2SWMM - INP Exporter Module
Generates input files for EPA SWMM 5.2 compatible format
"""

from typing import List, Dict, Tuple


class SWMMExporter:
    """
    Exports SWMM data to .inp format compatible with EPA SWMM 5.2
    """

    def __init__(self, project_title: str = "SWMM Drainage Project"):
        self.project_title = project_title

    def set_title(self, title: str):
        """Sets project title."""
        self.project_title = title

    def _safe_float(self, value):
        """Safely converts any value to float."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _safe_str(self, value):
        """Safely converts any value to string."""
        if value is None:
            return ""
        return str(value).strip()

    def export_to_file(self, filepath: str, nodes_data: List[Dict],
                       links_data: List[Dict], subcatchments_data: List[Dict]) -> Tuple[bool, str]:
        """
        Exports data to SWMM 5.2 .inp file.
        """
        try:
            lines = []

            # TITLE
            lines.append("[TITLE]")
            lines.append(f";;{self.project_title}")
            lines.append("")

            # OPTIONS
            lines.append("[OPTIONS]")
            lines.append(";;Option             Value")
            lines.append("FLOW_UNITS           CMS")
            lines.append("INFILTRATION         GREEN_AMPT")
            lines.append("FLOW_ROUTING         KINWAVE")
            lines.append("LINK_OFFSETS         DEPTH")
            lines.append("MIN_SLOPE            0.0")
            lines.append("ALLOW_PONDING        NO")
            lines.append("")

            # REPORT
            lines.append("[REPORT]")
            lines.append(";;Reporting Options")
            lines.append("SUBCATCHMENTS ALL")
            lines.append("NODES ALL")
            lines.append("LINKS ALL")
            lines.append("")

            # JUNCTIONS
            lines.append("[JUNCTIONS]")
            lines.append(";;Name           Elevation  MaxDepth   InitDepth  SurDepth   Aponded")
            lines.append(";;-------------- ---------- ---------- ---------- ---------- ----------")
            for node in nodes_data:
                name     = self._safe_str(node.get('ID', 'NODE'))
                elev     = self._safe_float(node.get('InvertElev', 0.0))
                maxdepth = self._safe_float(node.get('MaxDepth', 1.0))
                lines.append(f"{name:<15} {elev:>10.2f} {maxdepth:>10.2f} 0          0          0")
            lines.append("")

            # CONDUITS
            lines.append("[CONDUITS]")
            lines.append(";;Name           From Node        To Node          Length     Roughness  InOffset   OutOffset  InitFlow   MaxFlow")
            lines.append(";;-------------- ---------------- ---------------- ---------- ---------- ---------- ---------- ---------- ----------")
            for link in links_data:
                name       = self._safe_str(link.get('ID', 'LINK'))
                node1      = self._safe_str(link.get('InletNode', ''))
                node2      = self._safe_str(link.get('OutletNode', ''))
                length     = self._safe_float(link.get('Length', 100.0))
                n          = self._safe_float(link.get('ManningN', 0.009))
                in_offset  = self._safe_float(link.get('InOffset', 0.0))
                out_offset = self._safe_float(link.get('OutOffset', 0.0))
                lines.append(f"{name:<15} {node1:<17} {node2:<17} {length:>10.2f} {n:>10.3f} {in_offset:>10.2f} {out_offset:>10.2f} 0          0")
            lines.append("")

            # XSECTIONS
            lines.append("[XSECTIONS]")
            lines.append(";;Link           Shape        Geom1            Geom2      Geom3      Geom4      Barrels    Culvert")
            lines.append(";;-------------- ------------ ---------------- ---------- ---------- ---------- ---------- ----------")
            for link in links_data:
                link_id = self._safe_str(link.get('ID', 'LINK'))
                lines.append(f"{link_id:<15} CIRCULAR     1                0          0          0          1")
            lines.append("")

            # SUBCATCHMENTS
            # RainGage and Outlet are read from layer attributes as entered by the user.
            # If left blank in QGIS they will be blank here - assign them in SWMM after import.
            lines.append("[SUBCATCHMENTS]")
            lines.append(";;Name           Rain Gage        Outlet           Area     %Imperv  Width    %Slope   CurbLen  SnowPack")
            lines.append(";;-------------- ---------------- ---------------- -------- -------- -------- -------- -------- --------")
            for subcat in subcatchments_data:
                name        = self._safe_str(subcat.get('ID', 'SUB'))
                rain_gage   = self._safe_str(subcat.get('RainGage', ''))
                outlet      = self._safe_str(subcat.get('Outlet', ''))
                area        = self._safe_float(subcat.get('Area', 1.0))
                perc_imperv = self._safe_float(subcat.get('PercImperv', 0.0))
                width       = self._safe_float(subcat.get('Width', 50.0))
                slope       = self._safe_float(subcat.get('Slope', 0.01))
                lines.append(
                    f"{name:<15} {rain_gage:<17} {outlet:<17} "
                    f"{area:>8.2f} {perc_imperv:>8.1f} {width:>8.2f} {slope:>8.2f} 0"
                )
            lines.append("")

            # COORDINATES
            lines.append("[COORDINATES]")
            lines.append(";;Node           X-Coord            Y-Coord")
            lines.append(";;-------------- ------------------ ------------------")
            for node in nodes_data:
                name = self._safe_str(node.get('ID', 'NODE'))
                x    = self._safe_float(node.get('X', 0.0))
                y    = self._safe_float(node.get('Y', 0.0))
                lines.append(f"{name:<15} {x:>18.3f} {y:>18.3f}")
            lines.append("")

            # POLYGONS (Subcatchment vertices)
            lines.append("[Polygons]")
            lines.append(";;Subcatchment   X-Coord            Y-Coord")
            lines.append(";;-------------- ------------------ ------------------")
            for subcat in subcatchments_data:
                name     = self._safe_str(subcat.get('ID', 'SUB'))
                vertices = subcat.get('vertices', [])

                if not vertices:
                    continue

                # Remove duplicate closing vertex if present
                if len(vertices) > 1 and vertices[0] == vertices[-1]:
                    vertices = vertices[:-1]

                for vertex in vertices:
                    x = self._safe_float(vertex.get('x', 0.0))
                    y = self._safe_float(vertex.get('y', 0.0))
                    lines.append(f"{name:<15} {x:>18.3f} {y:>18.3f}")
            lines.append("")

            # Write file
            content = "\n".join(lines)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            return True, (
                f"File exported successfully:\n{filepath}\n\n"
                f"Nodes: {len(nodes_data)}\n"
                f"Links: {len(links_data)}\n"
                f"Subcatchments: {len(subcatchments_data)}\n\n"
                f"Note: Complete RAINGAGES, SUBAREAS and INFILTRATION sections in SWMM."
            )

        except Exception as e:
            return False, f"Export failed:\n{str(e)}"
