# -*- coding: utf-8 -*-
"""
QGIS2SWMM - Core Module
Business logic: layer management, topology, geometry calculations, data extraction
"""

from typing import List, Dict, Tuple, Optional
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsField, QgsFeature,
    QgsGeometry, QgsPointXY, QgsWkbTypes, QgsCoordinateReferenceSystem,
    QgsSpatialIndex, QgsRasterDataProvider
)
from qgis.PyQt.QtCore import QVariant
import math


class SWMMCore:
    """
    Core logic for QGIS2SWMM.
    Manages layers, topology detection, geometry calculations and data extraction.
    """

    # Layer names
    NODES_LAYER_NAME = "SWMM_Nodes"
    LINKS_LAYER_NAME = "SWMM_Links"
    SUBCATCHMENTS_LAYER_NAME = "SWMM_Subcatchments"

    def __init__(self):
        self.nodes_layer: Optional[QgsVectorLayer] = None
        self.links_layer: Optional[QgsVectorLayer] = None
        self.subcatchments_layer: Optional[QgsVectorLayer] = None
        self._find_existing_layers()

    # =========================================================================
    # LAYER DISCOVERY
    # =========================================================================

    def _find_existing_layers(self):
        """Searches for already-loaded SWMM layers in the current project."""
        for layer in QgsProject.instance().mapLayers().values():
            if not isinstance(layer, QgsVectorLayer):
                continue
            name = layer.name()
            if name == self.NODES_LAYER_NAME:
                self.nodes_layer = layer
            elif name == self.LINKS_LAYER_NAME:
                self.links_layer = layer
            elif name == self.SUBCATCHMENTS_LAYER_NAME:
                self.subcatchments_layer = layer

    # =========================================================================
    # CRS VALIDATION
    # =========================================================================

    def validate_crs_is_projected(self) -> Tuple[bool, str]:
        """
        Validates that the project CRS is projected (metric units).
        Returns (is_valid, message).
        """
        crs = QgsProject.instance().crs()
        if not crs.isValid():
            return False, "Project CRS is not defined. Set a valid projected CRS."
        if crs.isGeographic():
            return False, (
                f"CRS '{crs.description()}' is geographic (degrees). "
                "Use a projected CRS with metric units (e.g. UTM, EPSG:32718)."
            )
        return True, f"CRS OK: {crs.description()} [{crs.authid()}]"

    # =========================================================================
    # LAYER INITIALIZATION
    # =========================================================================

    def initialize_swmm_layers(self, output_directory: str):
        """
        Creates the three SWMM vector layers (Nodes, Links, Subcatchments),
        saves them as GeoPackage files and adds them to the project.
        """
        import os

        crs = QgsProject.instance().crs()
        crs_str = crs.authid()

        # ---- NODES (Point) ----
        nodes_path = os.path.join(output_directory, "SWMM_Nodes.gpkg")
        nodes_layer = QgsVectorLayer(f"Point?crs={crs_str}", self.NODES_LAYER_NAME, "memory")
        nodes_fields = [
            QgsField("ID",         QVariant.String, len=20),
            QgsField("InvertElev", QVariant.Double),
            QgsField("MaxDepth",   QVariant.Double),
            QgsField("X",          QVariant.Double),
            QgsField("Y",          QVariant.Double),
        ]
        nodes_layer.dataProvider().addAttributes(nodes_fields)
        nodes_layer.updateFields()
        self._save_layer_to_gpkg(nodes_layer, nodes_path, self.NODES_LAYER_NAME)
        saved_nodes = QgsVectorLayer(nodes_path, self.NODES_LAYER_NAME, "ogr")

        # ---- LINKS (LineString) ----
        links_path = os.path.join(output_directory, "SWMM_Links.gpkg")
        links_layer = QgsVectorLayer(f"LineString?crs={crs_str}", self.LINKS_LAYER_NAME, "memory")
        links_fields = [
            QgsField("ID",         QVariant.String, len=20),
            QgsField("InletNode",  QVariant.String, len=20),
            QgsField("OutletNode", QVariant.String, len=20),
            QgsField("Length",     QVariant.Double),
            QgsField("ManningN",   QVariant.Double),
            QgsField("InOffset",   QVariant.Double),
            QgsField("OutOffset",  QVariant.Double),
        ]
        links_layer.dataProvider().addAttributes(links_fields)
        links_layer.updateFields()
        self._save_layer_to_gpkg(links_layer, links_path, self.LINKS_LAYER_NAME)
        saved_links = QgsVectorLayer(links_path, self.LINKS_LAYER_NAME, "ogr")

        # ---- SUBCATCHMENTS (Polygon) ----
        subcat_path = os.path.join(output_directory, "SWMM_Subcatchments.gpkg")
        subcat_layer = QgsVectorLayer(f"Polygon?crs={crs_str}", self.SUBCATCHMENTS_LAYER_NAME, "memory")
        subcat_fields = [
            QgsField("ID",         QVariant.String, len=20),
            QgsField("RainGage",   QVariant.String, len=20),
            QgsField("Outlet",     QVariant.String, len=20),
            QgsField("Area",       QVariant.Double),
            QgsField("PercImperv", QVariant.Double),
            QgsField("Width",      QVariant.Double),
            QgsField("Slope",      QVariant.Double),
        ]
        subcat_layer.dataProvider().addAttributes(subcat_fields)
        subcat_layer.updateFields()
        self._save_layer_to_gpkg(subcat_layer, subcat_path, self.SUBCATCHMENTS_LAYER_NAME)
        saved_subcat = QgsVectorLayer(subcat_path, self.SUBCATCHMENTS_LAYER_NAME, "ogr")

        # Add to project
        QgsProject.instance().addMapLayer(saved_nodes)
        QgsProject.instance().addMapLayer(saved_links)
        QgsProject.instance().addMapLayer(saved_subcat)

        self.nodes_layer = saved_nodes
        self.links_layer = saved_links
        self.subcatchments_layer = saved_subcat

    def _save_layer_to_gpkg(self, layer: QgsVectorLayer, path: str, layer_name: str):
        """Saves a memory layer to a GeoPackage file."""
        from qgis.core import QgsVectorFileWriter, QgsCoordinateTransformContext
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = layer_name
        options.fileEncoding = "UTF-8"
        QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, path,
            QgsCoordinateTransformContext(),
            options
        )

    # =========================================================================
    # AUTO ID GENERATION
    # =========================================================================

    def generate_auto_ids(self) -> Dict[str, int]:
        """
        Fills empty ID fields automatically:
        Nodes → N1, N2 ...   Links → L1, L2 ...   Subcatchments → S1, S2 ...
        Returns counts of generated IDs per layer type.
        """
        self._find_existing_layers()
        counts = {'nodes': 0, 'links': 0, 'subcatchments': 0}
        counts['nodes']         = self._fill_ids(self.nodes_layer,         prefix='N')
        counts['links']         = self._fill_ids(self.links_layer,         prefix='L')
        counts['subcatchments'] = self._fill_ids(self.subcatchments_layer, prefix='S')
        return counts

    def _fill_ids(self, layer: Optional[QgsVectorLayer], prefix: str) -> int:
        """Fills empty ID fields in a layer with sequential IDs."""
        if not layer:
            return 0

        # Collect existing IDs to avoid duplicates
        existing = set()
        for feat in layer.getFeatures():
            val = feat['ID']
            if val and str(val).strip():
                existing.add(str(val).strip())

        counter = 1
        generated = 0
        layer.startEditing()
        id_idx = layer.fields().indexFromName('ID')

        for feat in layer.getFeatures():
            val = feat['ID']
            if not val or not str(val).strip():
                while f"{prefix}{counter}" in existing:
                    counter += 1
                new_id = f"{prefix}{counter}"
                layer.changeAttributeValue(feat.id(), id_idx, new_id)
                existing.add(new_id)
                counter += 1
                generated += 1

        layer.commitChanges()
        return generated

    # =========================================================================
    # ELEVATIONS FROM DEM
    # =========================================================================

    def sync_elevations_from_dem(self, dem_layer: QgsRasterLayer) -> Dict:
        """
        Reads elevation from DEM raster at each node's location
        and writes it to the InvertElev field.
        Returns a summary dict with keys: total_nodes, successful, outside_dem, message.
        """
        self._find_existing_layers()
        if not self.nodes_layer:
            return {'_summary': {'total_nodes': 0, 'successful': 0, 'outside_dem': 0,
                                 'message': 'Nodes layer not found.'}}

        provider = dem_layer.dataProvider()
        extent   = dem_layer.extent()

        total      = 0
        successful = 0
        outside    = 0

        elev_idx = self.nodes_layer.fields().indexFromName('InvertElev')
        x_idx    = self.nodes_layer.fields().indexFromName('X')
        y_idx    = self.nodes_layer.fields().indexFromName('Y')

        self.nodes_layer.startEditing()

        for feat in self.nodes_layer.getFeatures():
            total += 1
            point = feat.geometry().asPoint()
            x, y  = point.x(), point.y()

            # Store coordinates in attributes
            self.nodes_layer.changeAttributeValue(feat.id(), x_idx, round(x, 3))
            self.nodes_layer.changeAttributeValue(feat.id(), y_idx, round(y, 3))

            if not extent.contains(QgsPointXY(x, y)):
                outside += 1
                continue

            result, ok = provider.sample(QgsPointXY(x, y), 1)
            if ok and result is not None:
                self.nodes_layer.changeAttributeValue(feat.id(), elev_idx, round(result, 3))
                successful += 1
            else:
                outside += 1

        self.nodes_layer.commitChanges()

        summary = {
            'total_nodes': total,
            'successful':  successful,
            'outside_dem': outside,
            'message': f"Updated {successful}/{total} nodes. {outside} outside DEM bounds."
        }
        return {'_summary': summary}

    # =========================================================================
    # LINK TOPOLOGY (AUTO SNAP)
    # =========================================================================

    def auto_snap_links_to_nodes(self, snap_distance: float = 10.0) -> Dict[str, Tuple[str, str]]:
        """
        Detects InletNode and OutletNode for each link by finding the closest
        node to its start and end vertices within snap_distance (meters).
        Returns dict: {link_id: (inlet_node_id, outlet_node_id)}
        """
        self._find_existing_layers()
        if not self.links_layer or not self.nodes_layer:
            return {}

        # Build spatial index for nodes
        node_index = QgsSpatialIndex()
        node_map: Dict[int, QgsFeature] = {}
        for feat in self.nodes_layer.getFeatures():
            node_index.insertFeature(feat)
            node_map[feat.id()] = feat

        inlet_idx  = self.links_layer.fields().indexFromName('InletNode')
        outlet_idx = self.links_layer.fields().indexFromName('OutletNode')

        snapped: Dict[str, Tuple[str, str]] = {}
        self.links_layer.startEditing()

        for link_feat in self.links_layer.getFeatures():
            geom = link_feat.geometry()
            if geom.isEmpty():
                continue

            vertices = list(geom.vertices())
            if len(vertices) < 2:
                continue

            start_pt = QgsPointXY(vertices[0].x(),  vertices[0].y())
            end_pt   = QgsPointXY(vertices[-1].x(), vertices[-1].y())

            inlet_id  = self._find_nearest_node(start_pt, snap_distance, node_index, node_map)
            outlet_id = self._find_nearest_node(end_pt,   snap_distance, node_index, node_map)

            link_id = str(link_feat['ID']) if link_feat['ID'] else str(link_feat.id())

            if inlet_id or outlet_id:
                self.links_layer.changeAttributeValue(link_feat.id(), inlet_idx,  inlet_id  or '')
                self.links_layer.changeAttributeValue(link_feat.id(), outlet_idx, outlet_id or '')
                snapped[link_id] = (inlet_id or '', outlet_id or '')

        self.links_layer.commitChanges()
        return snapped

    def _find_nearest_node(self, point: QgsPointXY, max_dist: float,
                           index: QgsSpatialIndex, node_map: Dict) -> str:
        """Returns the ID of the nearest node within max_dist, or empty string."""
        candidates = index.nearestNeighbor(point, 1)
        if not candidates:
            return ''
        node_feat = node_map[candidates[0]]
        node_pt   = node_feat.geometry().asPoint()
        dist = point.distance(node_pt)
        if dist <= max_dist:
            return str(node_feat['ID']) if node_feat['ID'] else ''
        return ''

    # =========================================================================
    # LINK LENGTH
    # =========================================================================

    def auto_calculate_link_length(self) -> Dict[str, float]:
        """
        Calculates the geometric length of each link and writes it to the Length field.
        Returns dict: {link_id: length_meters}
        """
        self._find_existing_layers()
        if not self.links_layer:
            return {}

        length_idx = self.links_layer.fields().indexFromName('Length')
        results: Dict[str, float] = {}

        self.links_layer.startEditing()
        for feat in self.links_layer.getFeatures():
            length = feat.geometry().length()
            self.links_layer.changeAttributeValue(feat.id(), length_idx, round(length, 3))
            link_id = str(feat['ID']) if feat['ID'] else str(feat.id())
            results[link_id] = round(length, 3)

        self.links_layer.commitChanges()
        return results

    # =========================================================================
    # SUBCATCHMENT CALCULATIONS
    # =========================================================================

    def auto_calculate_subcatchment_area(self) -> Dict[str, float]:
        """
        Calculates the geometric area of each subcatchment polygon (in hectares)
        and writes it to the Area field.
        Returns dict: {subcat_id: area_ha}
        """
        self._find_existing_layers()
        if not self.subcatchments_layer:
            return {}

        area_idx = self.subcatchments_layer.fields().indexFromName('Area')
        results: Dict[str, float] = {}

        self.subcatchments_layer.startEditing()
        for feat in self.subcatchments_layer.getFeatures():
            area_m2 = feat.geometry().area()
            area_ha = round(area_m2 / 10000.0, 4)
            self.subcatchments_layer.changeAttributeValue(feat.id(), area_idx, area_ha)
            sc_id = str(feat['ID']) if feat['ID'] else str(feat.id())
            results[sc_id] = area_ha

        self.subcatchments_layer.commitChanges()
        return results

    def auto_calculate_subcatchment_slope_and_width(self, dem_layer: QgsRasterLayer) -> Dict[str, Dict]:
        """
        Estimates representative slope (%) and characteristic width (m) for each
        subcatchment using the DEM. Width is approximated as Area / max_flow_length.
        Returns dict: {subcat_id: {'slope': float, 'width': float}}
        """
        self._find_existing_layers()
        if not self.subcatchments_layer or not dem_layer:
            return {}

        provider  = dem_layer.dataProvider()
        slope_idx = self.subcatchments_layer.fields().indexFromName('Slope')
        width_idx = self.subcatchments_layer.fields().indexFromName('Width')
        results: Dict[str, Dict] = {}

        self.subcatchments_layer.startEditing()

        for feat in self.subcatchments_layer.getFeatures():
            geom    = feat.geometry()
            bbox    = geom.boundingBox()
            area_m2 = geom.area()

            # Sample elevations inside polygon to estimate slope
            elevations = self._sample_elevations_in_polygon(geom, bbox, provider, samples=25)

            if len(elevations) >= 2:
                elev_range = max(elevations) - min(elevations)
                char_len   = max(bbox.width(), bbox.height())
                slope_pct  = round((elev_range / char_len) * 100.0, 2) if char_len > 0 else 0.5
            else:
                slope_pct = 0.5  # default fallback

            # Width = Area / characteristic length (EPA recommended method)
            char_len = max(bbox.width(), bbox.height())
            width    = round(area_m2 / char_len, 2) if char_len > 0 else round(math.sqrt(area_m2), 2)

            sc_id = str(feat['ID']) if feat['ID'] else str(feat.id())
            self.subcatchments_layer.changeAttributeValue(feat.id(), slope_idx, slope_pct)
            self.subcatchments_layer.changeAttributeValue(feat.id(), width_idx, width)
            results[sc_id] = {'slope': slope_pct, 'width': width}

        self.subcatchments_layer.commitChanges()
        return results

    def _sample_elevations_in_polygon(self, geom: QgsGeometry, bbox,
                                      provider: QgsRasterDataProvider,
                                      samples: int = 25) -> List[float]:
        """Samples DEM elevations on a regular grid inside the polygon."""
        elevations = []
        cols = rows = int(math.sqrt(samples))
        dx = bbox.width()  / cols
        dy = bbox.height() / rows

        for i in range(cols):
            for j in range(rows):
                x  = bbox.xMinimum() + dx * (i + 0.5)
                y  = bbox.yMinimum() + dy * (j + 0.5)
                pt = QgsPointXY(x, y)
                if geom.contains(QgsGeometry.fromPointXY(pt)):
                    val, ok = provider.sample(pt, 1)
                    if ok and val is not None:
                        elevations.append(val)

        return elevations

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def validate_layer_completeness(self) -> Dict[str, List[str]]:
        """
        Checks that all required fields are filled in all features.
        Returns dict: {layer_name: [list of error messages]}
        """
        self._find_existing_layers()
        errors: Dict[str, List[str]] = {
            'Nodes': [],
            'Links': [],
            'Subcatchments': []
        }

        # Nodes
        if self.nodes_layer:
            for feat in self.nodes_layer.getFeatures():
                fid = feat['ID'] or f"fid={feat.id()}"
                if not feat['ID']:
                    errors['Nodes'].append(f"{fid}: missing ID")
                if feat['InvertElev'] is None:
                    errors['Nodes'].append(f"{fid}: missing InvertElev")
        else:
            errors['Nodes'].append("Layer not found")

        # Links
        if self.links_layer:
            for feat in self.links_layer.getFeatures():
                fid = feat['ID'] or f"fid={feat.id()}"
                if not feat['ID']:
                    errors['Links'].append(f"{fid}: missing ID")
                if not feat['InletNode']:
                    errors['Links'].append(f"{fid}: missing InletNode")
                if not feat['OutletNode']:
                    errors['Links'].append(f"{fid}: missing OutletNode")
                if not feat['Length'] or feat['Length'] == 0:
                    errors['Links'].append(f"{fid}: Length is 0 or missing")
        else:
            errors['Links'].append("Layer not found")

        # Subcatchments
        if self.subcatchments_layer:
            for feat in self.subcatchments_layer.getFeatures():
                fid = feat['ID'] or f"fid={feat.id()}"
                if not feat['ID']:
                    errors['Subcatchments'].append(f"{fid}: missing ID")
                if not feat['Area'] or feat['Area'] == 0:
                    errors['Subcatchments'].append(f"{fid}: Area is 0 or missing")
                if not feat['Width'] or feat['Width'] == 0:
                    errors['Subcatchments'].append(f"{fid}: Width is 0 or missing")
                if not feat['Slope'] or feat['Slope'] == 0:
                    errors['Subcatchments'].append(f"{fid}: Slope is 0 or missing")
        else:
            errors['Subcatchments'].append("Layer not found")

        return errors

    # =========================================================================
    # DATA EXTRACTION FOR EXPORT
    # =========================================================================

    def get_nodes_data(self) -> List[Dict]:
        """Gets all nodes data as list of dictionaries."""
        self._find_existing_layers()
        if not self.nodes_layer:
            return []

        data = []
        for feature in self.nodes_layer.getFeatures():
            point = feature.geometry().asPoint()
            data.append({
                'ID':         feature['ID'],
                'InvertElev': feature['InvertElev'],
                'MaxDepth':   feature['MaxDepth'],
                'X':          feature['X'] if feature['X'] else point.x(),
                'Y':          feature['Y'] if feature['Y'] else point.y(),
            })
        return data

    def get_links_data(self) -> List[Dict]:
        """Gets all links data as list of dictionaries."""
        self._find_existing_layers()
        if not self.links_layer:
            return []

        data = []
        for feature in self.links_layer.getFeatures():
            data.append({
                'ID':         feature['ID'],
                'InletNode':  feature['InletNode'],
                'OutletNode': feature['OutletNode'],
                'Length':     feature['Length'],
                'ManningN':   feature['ManningN'],
                'InOffset':   feature['InOffset'],
                'OutOffset':  feature['OutOffset'],
            })
        return data

    def get_subcatchments_data(self) -> List[Dict]:
        """Gets all subcatchments data as list of dictionaries including polygon vertices."""
        self._find_existing_layers()
        if not self.subcatchments_layer:
            return []

        data = []
        for feature in self.subcatchments_layer.getFeatures():
            geom     = feature.geometry()
            vertices = []
            if not geom.isEmpty():
                if geom.isMultipart():
                    polygons = geom.asMultiPolygon()
                    for polygon in polygons:
                        for ring in polygon:
                            for point in ring:
                                vertices.append({'x': point.x(), 'y': point.y()})
                else:
                    polygon = geom.asPolygon()
                    if polygon:
                        for ring in polygon:
                            for point in ring:
                                vertices.append({'x': point.x(), 'y': point.y()})

            data.append({
                'ID':         feature['ID'],
                'RainGage':   feature['RainGage'],
                'Outlet':     feature['Outlet'],
                'Area':       feature['Area'],
                'PercImperv': feature['PercImperv'],
                'Width':      feature['Width'],
                'Slope':      feature['Slope'],
                'vertices':   vertices
            })
        return data
