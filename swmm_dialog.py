# -*- coding: utf-8 -*-
"""
QGIS2SWMM - GUI Module
Dialogs and widgets for user interaction
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFileDialog, QMessageBox, QProgressBar, QTextEdit,
    QTabWidget, QWidget, QDoubleSpinBox
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsRasterLayer
from .swmm_core import SWMMCore
from .swmm_exporter import SWMMExporter


class SWMMMainDialog(QDialog):
    """
    Main dialog for QGIS2SWMM plugin
    """

    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.core = SWMMCore()
        self.exporter = SWMMExporter()
        self.output_directory = None  # Store selected directory

        self.setWindowTitle("QGIS2SWMM v1.0")
        self.setGeometry(100, 100, 850, 750)

        self.setup_ui()

    def setup_ui(self):
        """Builds the user interface."""
        # Initialize log_output first so log_message() can be called
        # safely from any part of setup_ui (e.g. populate_raster_layers)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        main_layout = QVBoxLayout()

        # ==================== TABS ====================
        self.tabs = QTabWidget()

        # ==================== TAB 1: PROJECT SETUP ====================
        tab1 = QWidget()
        layout1 = QVBoxLayout()

        label1 = QLabel("1. PROJECT SETUP AND INITIALIZATION")
        label1.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout1.addWidget(label1)

        # CRS Validation
        btn_validate_crs = QPushButton("Step 1: Validate Project CRS")
        btn_validate_crs.clicked.connect(self.on_validate_crs)
        layout1.addWidget(btn_validate_crs)

        self.label_crs_status = QLabel("CRS Status: Not checked")
        self.label_crs_status.setStyleSheet("color: gray;")
        layout1.addWidget(self.label_crs_status)

        # Select Output Directory
        btn_select_dir = QPushButton("Step 1b: Select Output Directory for Layers")
        btn_select_dir.clicked.connect(self.on_select_output_directory)
        layout1.addWidget(btn_select_dir)

        self.label_dir_status = QLabel("Output Directory: Not selected")
        self.label_dir_status.setStyleSheet("color: gray;")
        layout1.addWidget(self.label_dir_status)

        # Initialize Layers
        btn_init_layers = QPushButton("Step 2: Initialize SWMM Layers")
        btn_init_layers.clicked.connect(self.on_initialize_layers)
        layout1.addWidget(btn_init_layers)

        self.label_layers_status = QLabel("Layers Status: Not created")
        self.label_layers_status.setStyleSheet("color: gray;")
        layout1.addWidget(self.label_layers_status)

        layout1.addStretch()
        tab1.setLayout(layout1)
        self.tabs.addTab(tab1, "Setup")

        # ==================== TAB 2: AUTO ID GENERATION ====================
        tab2 = QWidget()
        layout2 = QVBoxLayout()

        label2 = QLabel("2. AUTOMATIC ID GENERATION")
        label2.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout2.addWidget(label2)

        info_label = QLabel(
            "Generate automatic IDs after digitization:\n"
            "• Nodes: N1, N2, N3...\n"
            "• Links: L1, L2, L3...\n"
            "• Subcatchments: S1, S2, S3...\n\n"
            "Only empty ID fields will be filled."
        )
        info_label.setStyleSheet("color: #555; font-size: 10px;")
        layout2.addWidget(info_label)

        btn_auto_id = QPushButton("Generate Auto IDs")
        btn_auto_id.clicked.connect(self.on_generate_auto_ids)
        layout2.addWidget(btn_auto_id)

        self.text_id_report = QTextEdit()
        self.text_id_report.setReadOnly(True)
        self.text_id_report.setMaximumHeight(150)
        layout2.addWidget(self.text_id_report)

        layout2.addStretch()
        tab2.setLayout(layout2)
        self.tabs.addTab(tab2, "Auto ID")

        # ==================== TAB 3: NODES ====================
        tab3 = QWidget()
        layout3 = QVBoxLayout()

        label3 = QLabel("3. NODES MANAGEMENT")
        label3.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout3.addWidget(label3)

        # DEM Selection
        label_dem = QLabel("Select DEM (Raster Layer):")
        layout3.addWidget(label_dem)

        self.combo_dem = QComboBox()
        self.populate_raster_layers()
        layout3.addWidget(self.combo_dem)

        btn_refresh_dem = QPushButton("Refresh DEM List")
        btn_refresh_dem.clicked.connect(self.populate_raster_layers)
        layout3.addWidget(btn_refresh_dem)

        # Sync Elevations
        btn_sync_elev = QPushButton("Synchronize Elevations from DEM")
        btn_sync_elev.clicked.connect(self.on_sync_elevations)
        layout3.addWidget(btn_sync_elev)

        self.progress_dem = QProgressBar()
        layout3.addWidget(self.progress_dem)

        self.text_elevation_report = QTextEdit()
        self.text_elevation_report.setReadOnly(True)
        self.text_elevation_report.setMaximumHeight(120)
        layout3.addWidget(self.text_elevation_report)

        layout3.addStretch()
        tab3.setLayout(layout3)
        self.tabs.addTab(tab3, "Nodes")

        # ==================== TAB 4: LINKS ====================
        tab4 = QWidget()
        layout4 = QVBoxLayout()

        label4 = QLabel("4. LINKS TOPOLOGY")
        label4.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout4.addWidget(label4)

        # Snap Configuration
        label_snap = QLabel("Snapping Distance (meters):")
        self.input_snap = QDoubleSpinBox()
        self.input_snap.setValue(10.0)
        self.input_snap.setMinimum(1.0)
        self.input_snap.setMaximum(100.0)
        layout4.addWidget(label_snap)
        layout4.addWidget(self.input_snap)

        # Auto Snap
        btn_snap = QPushButton("Detect InletNode/OutletNode (Auto Snap)")
        btn_snap.clicked.connect(self.on_auto_snap)
        layout4.addWidget(btn_snap)

        # Calculate Length
        btn_calc_length = QPushButton("Calculate Link Lengths")
        btn_calc_length.clicked.connect(self.on_calc_link_length)
        layout4.addWidget(btn_calc_length)

        self.progress_links = QProgressBar()
        layout4.addWidget(self.progress_links)

        self.text_links_report = QTextEdit()
        self.text_links_report.setReadOnly(True)
        self.text_links_report.setMaximumHeight(100)
        layout4.addWidget(self.text_links_report)

        layout4.addStretch()
        tab4.setLayout(layout4)
        self.tabs.addTab(tab4, "Links")

        # ==================== TAB 5: SUBCATCHMENTS ====================
        tab5 = QWidget()
        layout5 = QVBoxLayout()

        label5 = QLabel("5. SUBCATCHMENTS")
        label5.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout5.addWidget(label5)

        btn_calc_all = QPushButton("Calculate Areas, Slope and Width")
        btn_calc_all.clicked.connect(self.on_calc_subcatchment_all)
        layout5.addWidget(btn_calc_all)

        self.progress_subcat = QProgressBar()
        layout5.addWidget(self.progress_subcat)

        self.text_subcat_report = QTextEdit()
        self.text_subcat_report.setReadOnly(True)
        self.text_subcat_report.setMaximumHeight(150)
        layout5.addWidget(self.text_subcat_report)

        layout5.addStretch()
        tab5.setLayout(layout5)
        self.tabs.addTab(tab5, "Subcatchments")

        # ==================== TAB 6: EXPORT ====================
        tab6 = QWidget()
        layout6 = QVBoxLayout()

        label6 = QLabel("6. EXPORT TO .INP")
        label6.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout6.addWidget(label6)

        label_title = QLabel("Project Title:")
        self.input_title = QComboBox()
        self.input_title.setEditable(True)
        self.input_title.addItem("SWMM Drainage Project")
        layout6.addWidget(label_title)
        layout6.addWidget(self.input_title)

        btn_validate = QPushButton("Validate Data Completeness")
        btn_validate.clicked.connect(self.on_validate_completeness)
        layout6.addWidget(btn_validate)

        btn_export = QPushButton("Export to .INP File")
        btn_export.clicked.connect(self.on_export_inp)
        layout6.addWidget(btn_export)

        self.progress_export = QProgressBar()
        layout6.addWidget(self.progress_export)

        layout6.addStretch()
        tab6.setLayout(layout6)
        self.tabs.addTab(tab6, "Export")

        # ==================== TAB 7: LOG ====================
        tab7 = QWidget()
        layout7 = QVBoxLayout()

        label7 = QLabel("OPERATION LOG")
        label7.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout7.addWidget(label7)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout7.addWidget(self.log_output)

        btn_clear_log = QPushButton("Clear Log")
        btn_clear_log.clicked.connect(lambda: self.log_output.clear())
        layout7.addWidget(btn_clear_log)

        tab7.setLayout(layout7)
        self.tabs.addTab(tab7, "Log")

        # ==================== MAIN LAYOUT ====================
        main_layout.addWidget(self.tabs)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        bottom_layout.addStretch()
        bottom_layout.addWidget(btn_close)

        main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)

        self.log_message("QGIS2SWMM initialized", "INFO")

    def log_message(self, message: str, level: str = "INFO"):
        """Logs a message to the log output."""
        self.log_output.append(f"[{level}] {message}")

    def populate_raster_layers(self):
        """Loads available raster layers in the combo."""
        self.combo_dem.clear()
        raster_count = 0
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsRasterLayer):
                self.combo_dem.addItem(layer.name(), layer)
                raster_count += 1
        
        if raster_count == 0:
            self.combo_dem.addItem("No DEM loaded", None)
            self.log_message("⚠ No raster layers found. Load a DEM first.", "WARNING")

    # ==================== EVENT CALLBACKS ====================

    def on_select_output_directory(self):
        """Allows user to select output directory for layers."""
        try:
            directory = QFileDialog.getExistingDirectory(
                self,
                "Select Directory to Save SWMM Layers",
                "",
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            if directory:
                self.output_directory = directory
                self.label_dir_status.setText(f"Output Directory: {directory}")
                self.label_dir_status.setStyleSheet("color: green; font-weight: bold;")
                self.log_message(f"✓ Output directory selected: {directory}", "SUCCESS")
            else:
                self.log_message("⚠ Directory selection cancelled", "WARNING")
        except Exception as e:
            self.log_message(f"✗ Error selecting directory: {str(e)}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to select directory:\n{str(e)}")

    def on_validate_crs(self):
        """Validates project CRS."""
        try:
            is_valid, msg = self.core.validate_crs_is_projected()
            self.label_crs_status.setText(f"CRS Status: {msg}")
            
            if is_valid:
                self.label_crs_status.setStyleSheet("color: green; font-weight: bold;")
                self.log_message(f"✓ {msg}", "SUCCESS")
                QMessageBox.information(self, "CRS Validation", msg)
            else:
                self.label_crs_status.setStyleSheet("color: red; font-weight: bold;")
                self.log_message(f"✗ {msg}", "ERROR")
                QMessageBox.warning(self, "CRS Validation", msg)
        except Exception as e:
            self.log_message(f"✗ Error: {str(e)}", "ERROR")
            QMessageBox.critical(self, "Error", f"CRS validation failed:\n{str(e)}")

    def on_initialize_layers(self):
        """Creates initial SWMM layers."""
        try:
            # First validate CRS
            is_valid, msg = self.core.validate_crs_is_projected()
            if not is_valid:
                QMessageBox.warning(self, "CRS Error", f"Invalid CRS:\n{msg}\n\nValidate CRS first!")
                return

            # Check if directory is selected
            if not self.output_directory:
                QMessageBox.warning(self, "Directory Not Selected", 
                    "Please select an output directory first!\n\nClick 'Step 1b: Select Output Directory for Layers'")
                return

            self.core.initialize_swmm_layers(self.output_directory)
            
            self.label_layers_status.setText("Layers Status: ✓ Created successfully")
            self.label_layers_status.setStyleSheet("color: green; font-weight: bold;")
            
            self.log_message("✓ SWMM Layers created successfully", "SUCCESS")
            self.iface.messageBar().pushSuccess("SWMM", "Layers initialized (Nodes, Links, Subcatchments)")
            QMessageBox.information(self, "Success", f"SWMM layers created in:\n{self.output_directory}\n\n✓ Nodes (Point layer)\n✓ Links (LineString layer)\n✓ Subcatchments (Polygon layer)\n\nStart digitizing your drainage network.")
        except Exception as e:
            self.log_message(f"✗ Error: {str(e)}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to create layers:\n{str(e)}")

    def on_sync_elevations(self):
        """Synchronizes elevations from DEM."""
        try:
            dem_layer = self.combo_dem.currentData()
            if not dem_layer or not isinstance(dem_layer, QgsRasterLayer):
                raise ValueError("No valid DEM selected. Load a raster first!")

            self.progress_dem.setValue(0)
            self.log_message("Synchronizing elevations from DEM...", "INFO")

            results = self.core.sync_elevations_from_dem(dem_layer)

            # Build report
            summary = results.get('_summary', {})
            report = f"""ELEVATION SYNCHRONIZATION REPORT
{'='*40}
Total Nodes: {summary.get('total_nodes', 0)}
Successfully Updated: {summary.get('successful', 0)}
Outside DEM Bounds: {summary.get('outside_dem', 0)}

{summary.get('message', 'N/A')}
"""
            self.text_elevation_report.setText(report)
            self.progress_dem.setValue(100)

            self.log_message(f"✓ {summary.get('message', 'Elevations synchronized')}", "SUCCESS")

        except Exception as e:
            self.log_message(f"✗ Error: {str(e)}", "ERROR")
            QMessageBox.critical(self, "Error", f"Elevation sync failed:\n{str(e)}")

    def on_auto_snap(self):
        """Auto-detects node connections with improved algorithm."""
        try:
            snap_dist = self.input_snap.value()
            self.log_message("Detecting topology (snapping links to nodes)...", "INFO")

            snapped = self.core.auto_snap_links_to_nodes(snap_dist)

            report = f"""TOPOLOGY DETECTION REPORT
{'='*40}
Links Snapped: {len(snapped)}
Snap Distance: {snap_dist}m

Details:
"""
            if snapped:
                for link_id, (inlet, outlet) in snapped.items():
                    report += f"  ✓ {link_id}: {inlet} → {outlet}\n"
            else:
                report += "  No links snapped. Check if nodes exist and links are drawn.\n"

            self.text_links_report.setText(report)

            self.log_message(f"✓ {len(snapped)} links snapped to nodes", "SUCCESS")
            if len(snapped) > 0:
                QMessageBox.information(self, "Success", f"Snapped {len(snapped)} links to nodes")
            else:
                QMessageBox.warning(self, "No Snaps", "No links were snapped. Verify:\n• Nodes are digitized\n• Links are digitized\n• Links are close to nodes (within snap distance)")

        except Exception as e:
            self.log_message(f"✗ Error: {str(e)}", "ERROR")
            QMessageBox.critical(self, "Error", f"Topology detection failed:\n{str(e)}")

    def on_calc_link_length(self):
        """Calculates link lengths."""
        try:
            self.log_message("Calculating link lengths...", "INFO")
            results = self.core.auto_calculate_link_length()
            self.progress_links.setValue(100)
            
            report = f"""LINK LENGTH CALCULATION REPORT
{'='*40}
Total Links: {len(results)}

Details:
"""
            for link_id, length in results.items():
                report += f"  {link_id}: {length:.2f}m\n"

            self.text_links_report.setText(report)
            
            self.log_message(f"✓ {len(results)} link lengths calculated", "SUCCESS")
        except Exception as e:
            self.log_message(f"✗ Error: {str(e)}", "ERROR")

    def on_generate_auto_ids(self):
        """Generates automatic IDs."""
        try:
            self.log_message("Generating automatic IDs...", "INFO")
            results = self.core.generate_auto_ids()

            report = f"""AUTO ID GENERATION REPORT
{'='*40}
Nodes IDs Generated: {results['nodes']}
Links IDs Generated: {results['links']}
Subcatchments IDs Generated: {results['subcatchments']}

Generated IDs follow this pattern:
• Nodes: N1, N2, N3...
• Links: L1, L2, L3...
• Subcatchments: S1, S2, S3...
"""
            self.text_id_report.setText(report)

            self.log_message(f"✓ Generated {sum(results.values())} IDs", "SUCCESS")
            QMessageBox.information(self, "Success", f"Generated {sum(results.values())} automatic IDs")

        except Exception as e:
            self.log_message(f"✗ Error: {str(e)}", "ERROR")
            QMessageBox.critical(self, "Error", f"Auto ID generation failed:\n{str(e)}")

    def on_calc_subcatchment_all(self):
        """Calculates areas, slope and width in one step."""
        try:
            dem_layer = self.combo_dem.currentData()
            
            # Calculate area
            self.log_message("Calculating subcatchment areas...", "INFO")
            results_area = self.core.auto_calculate_subcatchment_area()
            self.progress_subcat.setValue(33)
            
            # Calculate slope and width
            self.log_message("Calculating slope and width...", "INFO")
            if dem_layer and isinstance(dem_layer, QgsRasterLayer):
                results_sw = self.core.auto_calculate_subcatchment_slope_and_width(dem_layer)
            else:
                results_sw = {}
                self.log_message("⚠ No valid DEM selected. Skipping slope/width calculation.", "WARNING")
            
            self.progress_subcat.setValue(100)
            
            # Build report
            report = f"""SUBCATCHMENT CALCULATION REPORT
{'='*40}
Total Subcatchments: {len(results_area)}

Details:
"""
            total_area = 0
            for sc_id, area in results_area.items():
                sw_data = results_sw.get(sc_id, {'slope': 0, 'width': 0})
                report += f"  {sc_id}:\n"
                report += f"    Area: {area:.4f} ha\n"
                report += f"    Slope: {sw_data['slope']:.2f}%\n"
                report += f"    Width: {sw_data['width']:.2f}m\n"
                total_area += area

            report += f"\nTotal Area: {total_area:.4f} ha"
            self.text_subcat_report.setText(report)
            
            self.log_message(f"✓ Calculations completed for {len(results_area)} subcatchments", "SUCCESS")
        except Exception as e:
            self.log_message(f"✗ Error: {str(e)}", "ERROR")
            QMessageBox.critical(self, "Error", str(e))

    def on_validate_completeness(self):
        """Validates data completeness."""
        try:
            errors = self.core.validate_layer_completeness()

            msg = "DATA VALIDATION REPORT:\n\n"
            has_errors = False
            
            for layer, layer_errors in errors.items():
                if layer_errors:
                    has_errors = True
                    msg += f"❌ {layer} ({len(layer_errors)} errors):\n"
                    for err in layer_errors[:5]:
                        msg += f"  - {err}\n"
                    if len(layer_errors) > 5:
                        msg += f"  ... and {len(layer_errors) - 5} more\n"
                else:
                    msg += f"✓ {layer}: OK\n"
                msg += "\n"

            self.log_message("Validation completed", "INFO")
            QMessageBox.information(self, "Validation Report", msg)
        except Exception as e:
            self.log_message(f"✗ Error: {str(e)}", "ERROR")

    def on_export_inp(self):
        """Exports data to .inp file."""
        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save SWMM File", "", "SWMM Files (*.inp);;All Files (*.*)"
            )
            if not filepath:
                return

            self.log_message("Exporting to .inp format...", "INFO")
            self.progress_export.setValue(25)

            # Get data
            nodes = self.core.get_nodes_data()
            links = self.core.get_links_data()
            subcatchments = self.core.get_subcatchments_data()

            self.progress_export.setValue(50)

            # Configure exporter
            title = self.input_title.currentText()
            self.exporter.set_title(title)

            self.progress_export.setValue(75)

            # Export
            success, msg = self.exporter.export_to_file(filepath, nodes, links, subcatchments)

            self.progress_export.setValue(100)

            if success:
                self.log_message(f"✓ File exported: {filepath}", "SUCCESS")
                QMessageBox.information(self, "Success", msg)
            else:
                self.log_message(f"✗ {msg}", "ERROR")
                QMessageBox.critical(self, "Error", msg)

        except Exception as e:
            self.log_message(f"✗ Error: {str(e)}", "ERROR")
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")

    def closeEvent(self, event):
        """Handles dialog close."""
        event.accept()