import os
import sys

import matplotlib
import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QApplication, QPushButton, QVBoxLayout, QWidget, QFileDialog,
                             QLabel, QHBoxLayout, QSlider, QGroupBox, QRadioButton, QButtonGroup,
                             QSpinBox, QCheckBox)
from imageio import get_reader
from matplotlib.patches import Circle
from skimage import io, color
from skimage.draw import disk

matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MatplotlibCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MatplotlibCanvas, self).__init__(self.fig)
        self.setParent(parent)
        self.fig.tight_layout()

    def display_image(self, image):
        self.axes.clear()
        self.axes.imshow(image)
        self.axes.axis('off')
        self.fig.tight_layout()
        self.draw()


class CircleSelector:
    def __init__(self, canvas, callback):
        self.canvas = canvas
        self.callback = callback
        self.start_point = None
        self.current_point = None
        self.circle = None
        self.line = None
        self.active = False
        self.diameter = 0

        # Connecter les événements
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)

    def on_press(self, event):
        if event.button == 1 and event.inaxes == self.canvas.axes:
            self.active = True
            self.start_point = (event.xdata, event.ydata)
            if self.circle:
                self.circle.remove()
                self.circle = None
            if self.line:
                self.line.remove()
                self.line = None
            self.canvas.draw()

    def on_motion(self, event):
        if self.active and event.inaxes == self.canvas.axes:
            self.current_point = (event.xdata, event.ydata)

            # Calculer le centre et le rayon
            center_x = (self.start_point[0] + self.current_point[0]) / 2
            center_y = (self.start_point[1] + self.current_point[1]) / 2

            # Calculer le diamètre (distance entre les deux points)
            self.diameter = np.sqrt((self.current_point[0] - self.start_point[0]) ** 2 +
                                    (self.current_point[1] - self.start_point[1]) ** 2)

            # Afficher le cercle et le diamètre
            if self.circle:
                self.circle.remove()
            if self.line:
                self.line.remove()

            # Dessiner le diamètre (ligne)
            self.line = self.canvas.axes.plot([self.start_point[0], self.current_point[0]],
                                              [self.start_point[1], self.current_point[1]],
                                              'r-', linewidth=1)[0]

            # Dessiner le cercle
            self.circle = self.canvas.axes.add_patch(
                Circle((center_x, center_y), self.diameter / 2,
                       edgecolor='red', facecolor='none', linewidth=1)
            )

            self.canvas.draw()

    def on_release(self, event):
        if self.active and event.button == 1 and event.inaxes == self.canvas.axes:
            self.active = False
            if self.start_point and self.current_point:
                # Calculer le centre
                center_x = (self.start_point[0] + self.current_point[0]) / 2
                center_y = (self.start_point[1] + self.current_point[1]) / 2

                # Appeler le callback avec les coordonnées du centre et le diamètre
                self.callback(center_x, center_y, self.diameter)


class VideoPlayer:
    def __init__(self, parent, canvas):
        self.parent = parent
        self.canvas = canvas
        self.video_reader = None
        self.current_frame = None
        self.total_frames = 0
        self.fps = 30
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)
        self.playing = False

    def load_video(self, file_path):
        try:
            # Utiliser imageio au lieu de cv2
            self.video_reader = get_reader(file_path)
            self.total_frames = self.video_reader.count_frames()
            self.original_fps = self.video_reader.get_meta_data()['fps']
            self.fps = self.original_fps
            self.current_frame_idx = 0

            # Lire la première image
            self.current_frame = self.video_reader.get_data(0)
            self.canvas.display_image(self.current_frame)
            return True
        except Exception as e:
            print(f"Erreur lors du chargement de la vidéo: {e}")
            return False

    def set_fps(self, fps):
        self.fps = fps
        if self.playing:
            self.timer.stop()
            self.timer.start(1000 // self.fps)

    def play(self):
        if not self.video_reader:
            return

        self.playing = True
        self.timer.start(1000 // self.fps)

    def pause(self):
        self.playing = False
        self.timer.stop()

    def next_frame(self):
        if not self.video_reader:
            return

        self.current_frame_idx += 1
        if self.current_frame_idx < self.total_frames:
            try:
                self.current_frame = self.video_reader.get_data(self.current_frame_idx)
                self.canvas.display_image(self.current_frame)
                self.parent.update_video_progress(self.current_frame_idx)
            except Exception as e:
                print(f"Erreur lors de la lecture de frame {self.current_frame_idx}: {e}")
                self.pause()
        else:
            # Fin de la vidéo, revenir au début
            self.current_frame_idx = 0
            self.current_frame = self.video_reader.get_data(0)
            self.canvas.display_image(self.current_frame)
            self.parent.update_video_progress(0)

    def seek(self, frame_idx):
        if not self.video_reader:
            return

        try:
            self.current_frame = self.video_reader.get_data(frame_idx)
            self.canvas.display_image(self.current_frame)
            self.current_frame_idx = frame_idx
        except Exception as e:
            print(f"Erreur lors de la recherche de frame {frame_idx}: {e}")

    def get_current_frame(self):
        return self.current_frame

    def close(self):
        if self.video_reader:
            self.pause()
            self.video_reader = None


class Main_window(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(120, 100, 1300, 800)
        self.setWindowTitle("Colored Pixels GUI")

        # Variables pour stocker les données d'image/vidéo
        self.original_image = None
        self.cropped_image = None
        self.image_path = None
        self.circle_coords = None
        self.current_display = None  # Pour suivre ce qui est affiché
        self.is_video = False

        # Créer la mise en page principale
        self.init_ui()

    def init_ui(self):
        # Layout principal
        self.global_layout = QVBoxLayout()

        # Layout pour les contrôles supérieurs
        self.controls_layout = QHBoxLayout()

        # Bouton pour charger une image ou vidéo
        self.load_image_button = QPushButton("Charger une image")
        self.load_image_button.clicked.connect(self.load_image)
        self.controls_layout.addWidget(self.load_image_button)

        self.load_video_button = QPushButton("Charger une vidéo")
        self.load_video_button.clicked.connect(self.load_video)
        self.controls_layout.addWidget(self.load_video_button)

        # Informations sur l'image/vidéo
        self.info_label = QLabel("Aucun média chargé")
        self.controls_layout.addWidget(self.info_label)

        # Ajouter les contrôles au layout principal
        self.global_layout.addLayout(self.controls_layout)

        # Ajouter les contrôles vidéo
        self.video_controls_layout = QHBoxLayout()

        self.play_button = QPushButton("Lecture")
        self.play_button.clicked.connect(self.play_video)
        self.play_button.setEnabled(False)
        self.video_controls_layout.addWidget(self.play_button)

        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_video)
        self.pause_button.setEnabled(False)
        self.video_controls_layout.addWidget(self.pause_button)

        self.fps_label = QLabel("FPS:")
        self.video_controls_layout.addWidget(self.fps_label)

        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setRange(1, 500)
        self.fps_spinbox.setValue(30)
        self.fps_spinbox.valueChanged.connect(self.change_fps)
        self.video_controls_layout.addWidget(self.fps_spinbox)

        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setEnabled(False)
        self.frame_slider.valueChanged.connect(self.seek_video)
        self.video_controls_layout.addWidget(self.frame_slider)

        self.frame_counter_label = QLabel("0/0")
        self.video_controls_layout.addWidget(self.frame_counter_label)


        self.global_layout.addLayout(self.video_controls_layout)

        # Layout pour l'affichage de l'image et les contrôles
        self.image_controls_layout = QHBoxLayout()

        # Zone d'affichage de l'image
        self.image_box = QGroupBox("Image")
        self.image_layout = QVBoxLayout()

        # Canvas Matplotlib pour l'affichage de l'image
        self.canvas = MatplotlibCanvas(self, width=8, height=6)
        self.image_layout.addWidget(self.canvas)

        # Contrôles d'affichage
        self.display_controls_layout = QHBoxLayout()

        self.reset_button = QPushButton("Réinitialiser l'affichage")
        self.reset_button.clicked.connect(self.reset_display)
        self.reset_button.setEnabled(False)
        self.display_controls_layout.addWidget(self.reset_button)

        # Option pour le diamètre double
        self.double_diameter_checkbox = QCheckBox("Rogner avec un diamètre double")
        self.double_diameter_checkbox.setChecked(True)
        self.display_controls_layout.addWidget(self.double_diameter_checkbox)

        self.image_layout.addLayout(self.display_controls_layout)

        self.image_box.setLayout(self.image_layout)
        self.image_controls_layout.addWidget(self.image_box, 3)  # 3:1 ratio pour l'image

        # Panneau de contrôle
        self.control_box = QGroupBox("Contrôles")
        self.control_layout = QVBoxLayout()

        # Options de filtre
        self.filter_group = QGroupBox("Options de filtre")
        self.filter_layout = QVBoxLayout()

        self.filter_options = QButtonGroup(self)
        self.no_filter = QRadioButton("Sans filtre")
        self.red_filter = QRadioButton("Filtre rouge")
        self.white_filter = QRadioButton("Filtre blanc")
        self.both_filter = QRadioButton("Filtres rouge et blanc")

        self.no_filter.setChecked(True)
        self.filter_options.addButton(self.no_filter)
        self.filter_options.addButton(self.red_filter)
        self.filter_options.addButton(self.white_filter)
        self.filter_options.addButton(self.both_filter)

        self.filter_layout.addWidget(self.no_filter)
        self.filter_layout.addWidget(self.red_filter)
        self.filter_layout.addWidget(self.white_filter)
        self.filter_layout.addWidget(self.both_filter)

        self.no_filter.toggled.connect(self.update_filter)
        self.red_filter.toggled.connect(self.update_filter)
        self.white_filter.toggled.connect(self.update_filter)
        self.both_filter.toggled.connect(self.update_filter)

        self.filter_group.setLayout(self.filter_layout)
        self.control_layout.addWidget(self.filter_group)

        # Sliders pour les seuils
        self.threshold_group = QGroupBox("Paramètres de seuil")
        self.threshold_layout = QVBoxLayout()

        # Slider pour le seuil de saturation
        self.saturation_label = QLabel("Seuil de saturation: 20%")
        self.saturation_slider = QSlider(Qt.Horizontal)
        self.saturation_slider.setMinimum(0)
        self.saturation_slider.setMaximum(100)
        self.saturation_slider.setValue(20)
        self.saturation_slider.setSingleStep(1)
        self.saturation_slider.setTickInterval(1)
        self.saturation_slider.setTickPosition(QSlider.TicksBelow)
        self.saturation_slider.valueChanged.connect(self.update_saturation_label)
        self.saturation_slider.valueChanged.connect(self.update_filter)

        # Slider pour le seuil de valeur
        self.value_label = QLabel("Seuil de valeur: 30%")
        self.value_slider = QSlider(Qt.Horizontal)
        self.value_slider.setMinimum(0)
        self.value_slider.setMaximum(100)
        self.value_slider.setValue(30)
        self.value_slider.setSingleStep(1)
        self.value_slider.setTickInterval(1)
        self.value_slider.setTickPosition(QSlider.TicksBelow)
        self.value_slider.valueChanged.connect(self.update_value_label)
        self.value_slider.valueChanged.connect(self.update_filter)

        self.threshold_layout.addWidget(self.saturation_label)
        self.threshold_layout.addWidget(self.saturation_slider)
        self.threshold_layout.addWidget(self.value_label)
        self.threshold_layout.addWidget(self.value_slider)

        self.threshold_group.setLayout(self.threshold_layout)
        self.control_layout.addWidget(self.threshold_group)

        # Statistiques
        self.stats_group = QGroupBox("Statistiques")
        self.stats_layout = QVBoxLayout()
        self.stats_label = QLabel("Aucune statistique disponible")
        self.stats_layout.addWidget(self.stats_label)
        self.stats_group.setLayout(self.stats_layout)
        self.control_layout.addWidget(self.stats_group)

        # Appliquer le layout du panneau de contrôle
        self.control_box.setLayout(self.control_layout)
        self.image_controls_layout.addWidget(self.control_box, 1)  # 3:1 ratio pour les contrôles

        # Ajouter le layout image+contrôles au layout principal
        self.global_layout.addLayout(self.image_controls_layout)

        # Appliquer le layout principal
        self.setLayout(self.global_layout)

        # Désactiver les contrôles initialement
        self.filter_group.setEnabled(False)
        self.threshold_group.setEnabled(False)

        # Créer le sélecteur de cercle
        self.circle_selector = CircleSelector(self.canvas, self.handle_selection)

        # Créer le lecteur vidéo
        self.video_player = VideoPlayer(self, self.canvas)

    def keyPressEvent(self, a0):
        if a0.key() == Qt.Key_Left and self.is_video:
            self.video_player.next_frame()
        if a0.key() == Qt.Key_Right and self.is_video:
            self.video_player.next_frame()

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir une image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
        )

        if file_path:
            try:
                self.is_video = False
                self.load_chosen_image(file_path)

                # Désactiver les contrôles vidéo
                self.play_button.setEnabled(False)
                self.pause_button.setEnabled(False)
                self.frame_slider.setEnabled(False)


                # Fermer toute vidéo ouverte
                self.video_player.close()

            except Exception as e:
                self.info_label.setText(f"Erreur lors du chargement: {str(e)}")

    def load_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir une vidéo", "",
            "Vidéos (*.mp4 *.avi *.mov *.mkv)"
        )

        if file_path:
            try:
                self.is_video = True
                self.image_path = file_path

                # Chargement de la vidéo
                if self.video_player.load_video(file_path):
                    # Mettre à jour l'info
                    file_name = os.path.basename(file_path)
                    self.fps_spinbox.setValue(int(self.video_player.original_fps))
                    self.info_label.setText(f"Vidéo: {file_name} ({self.video_player.total_frames} images)")

                    # Configurer le slider
                    self.frame_slider.setMinimum(0)
                    self.frame_slider.setMaximum(self.video_player.total_frames - 1)
                    self.frame_slider.setValue(0)
                    self.frame_counter_label.setText(f"0/{self.video_player.total_frames}")

                    # Activer les contrôles vidéo
                    self.play_button.setEnabled(True)
                    self.pause_button.setEnabled(True)
                    self.frame_slider.setEnabled(True)

                    self.reset_button.setEnabled(True)

                    # Réinitialiser les données de recadrage
                    self.cropped_image = None
                    self.circle_coords = None

                    # Mettre à jour l'affichage
                    self.current_display = "video"

                    # Store the first frame as original_image to allow immediate drawing
                    self.original_image = self.video_player.current_frame.copy()
                else:
                    self.info_label.setText("Erreur: Impossible de charger la vidéo")

            except Exception as e:
                self.info_label.setText(f"Erreur lors du chargement: {str(e)}")

    def load_chosen_image(self, file_path):
        self.image_path = file_path
        self.original_image = io.imread(file_path)

        # Mettre à jour l'info de l'image
        h, w = self.original_image.shape[:2]
        file_name = os.path.basename(file_path)
        self.info_label.setText(f"Image: {file_name} ({w}x{h})")

        # Afficher l'image
        self.canvas.display_image(self.original_image)
        self.current_display = "original"

        # Activer le bouton de reset
        self.reset_button.setEnabled(True)

        # Réinitialiser les données de recadrage
        self.cropped_image = None
        self.circle_coords = None

        # Désactiver les filtres
        self.filter_group.setEnabled(False)
        self.threshold_group.setEnabled(False)
        self.stats_label.setText("Aucune statistique disponible")

        # Réinitialiser le sélecteur de cercle
        self.circle_selector = CircleSelector(self.canvas, self.handle_selection)

    def play_video(self):
        self.video_player.play()

    def pause_video(self):
        self.video_player.pause()

    def change_fps(self, fps):
        self.video_player.set_fps(fps)

    def seek_video(self, frame_idx):
        self.video_player.seek(frame_idx)
        self.frame_counter_label.setText(f"{frame_idx}/{self.video_player.total_frames}")

        # Mettre à jour original_image avec la frame actuelle pour permettre le dessin immédiat
        self.original_image = self.video_player.current_frame.copy()

        # Si on était en train d'afficher une image recadrée, réinitialiser
        if self.current_display == "cropped" or self.current_display == "filtered":
            self.reset_display()

    def update_video_progress(self, frame_idx):
        self.frame_slider.setValue(frame_idx)
        self.frame_counter_label.setText(f"{frame_idx}/{self.video_player.total_frames}")

        # Mettre à jour original_image avec la frame actuelle pour permettre le dessin immédiat
        self.original_image = self.video_player.current_frame.copy()


    def handle_selection(self, center_x, center_y, diameter):
        # Quand on dessine sur une vidéo, pause automatiquement la vidéo pour permettre l'interaction
        if self.is_video and self.video_player.playing:
            self.video_player.pause()

        # Assurez-vous que original_image est à jour avec la frame actuelle si c'est une vidéo
        if self.is_video and self.video_player.current_frame is not None:
            self.original_image = self.video_player.current_frame.copy()

        if self.original_image is not None:
            # Déterminer le diamètre de rognage
            crop_diameter = diameter
            if self.double_diameter_checkbox.isChecked():
                crop_diameter = 2 * diameter

            # Stocker les coordonnées
            self.circle_coords = (center_x, center_y, crop_diameter)

            # Créer un masque de cercle pour le rognage
            h, w = self.original_image.shape[:2]
            rr, cc = disk((center_y, center_x), crop_diameter / 2, shape=(h, w))

            # Créer une image noire de même taille
            self.cropped_image = np.zeros_like(self.original_image)

            # Copier uniquement les pixels à l'intérieur du cercle
            self.cropped_image[rr, cc] = self.original_image[rr, cc]

            # Afficher l'image recadrée
            self.canvas.display_image(self.cropped_image)
            self.current_display = "cropped"

            # Activer les filtres
            self.filter_group.setEnabled(True)
            self.threshold_group.setEnabled(True)

            # Mettre à jour le message
            self.info_label.setText(
                f"Cercle sélectionné: Centre({int(center_x)},{int(center_y)}), Diamètre: {int(crop_diameter)}")

            # Mettre à jour les statistiques
            self.update_filter()

    def update_filter(self):
        if self.cropped_image is None:
            return

        # Récupérer les valeurs des sliders
        saturation_threshold = self.saturation_slider.value() / 100.0
        value_threshold = self.value_slider.value() / 100.0

        if saturation_threshold == 0 :
            saturation_threshold = 0.01
        if value_threshold == 0 :
            value_threshold = 0.01

            # Créer une copie de l'image recadrée
        filtered_image = np.copy(self.cropped_image)

        # Variables pour les statistiques
        # Compter uniquement les pixels non noirs (ceux à l'intérieur du cercle)
        non_black_pixels = np.count_nonzero(np.sum(self.cropped_image, axis=2))
        red_pixels = 0
        white_pixels = 0

        # Appliquer les filtres
        if self.red_filter.isChecked() or self.both_filter.isChecked():
            # Convertir en HSV
            hsv = color.rgb2hsv(self.cropped_image)

            # Masque pour le rouge (plages 0-0.1 et 0.8-1.0 en teinte)
            lower_red1, upper_red1 = 0.0, 0.1
            lower_red2, upper_red2 = 0.8, 1.0

            mask1 = ((hsv[:, :, 0] >= lower_red1) & (hsv[:, :, 0] <= upper_red1) &
                     (hsv[:, :, 1] >= saturation_threshold) & (hsv[:, :, 2] >= value_threshold))

            mask2 = ((hsv[:, :, 0] >= lower_red2) & (hsv[:, :, 0] <= upper_red2) &
                     (hsv[:, :, 1] >= saturation_threshold) & (hsv[:, :, 2] >= value_threshold))

            mask_red = mask1 | mask2
            red_pixels = np.count_nonzero(mask_red)

            if not self.both_filter.isChecked():
                # Appliquer le masque rouge uniquement
                mask_to_apply = np.stack([mask_red, mask_red, mask_red], axis=2)
                filtered_image = np.where(mask_to_apply, self.cropped_image, np.zeros_like(self.cropped_image))

        if self.white_filter.isChecked() or self.both_filter.isChecked():
            # Masque pour le blanc (toutes les composantes > 250)
            mask_white = np.all(self.cropped_image >= 250, axis=2)
            white_pixels = np.count_nonzero(mask_white)

            if not self.both_filter.isChecked() and self.white_filter.isChecked():
                # Appliquer le masque blanc uniquement
                mask_to_apply = np.stack([mask_white, mask_white, mask_white], axis=2)
                filtered_image = np.where(mask_to_apply, self.cropped_image, np.zeros_like(self.cropped_image))

        if self.both_filter.isChecked():
            # Appliquer les deux masques
            mask_combined = mask_red | mask_white
            mask_to_apply = np.stack([mask_combined, mask_combined, mask_combined], axis=2)
            filtered_image = np.where(mask_to_apply, self.cropped_image, np.zeros_like(self.cropped_image))

        # Mettre à jour les statistiques
        if non_black_pixels > 0:  # Pour éviter la division par zéro
            red_percentage = (red_pixels / non_black_pixels) * 100
            white_percentage = (white_pixels / non_black_pixels) * 100
            combined_percentage = ((red_pixels + white_pixels) / non_black_pixels) * 100
        else:
            red_percentage = white_percentage = combined_percentage = 0

        stats_text = ""
        if self.red_filter.isChecked() or self.both_filter.isChecked():
            stats_text += f"Pixels rouges: {red_pixels} ({red_percentage:.2f}%)\n"
        if self.white_filter.isChecked() or self.both_filter.isChecked():
            stats_text += f"Pixels blancs: {white_pixels} ({white_percentage:.2f}%)\n"
        if self.both_filter.isChecked():
            stats_text += f"Total filtré: {red_pixels + white_pixels} ({combined_percentage:.2f}%)"

        if not stats_text:
            stats_text = "Aucun filtre sélectionné"

        self.stats_label.setText(stats_text)

        # Afficher l'image correspondante
        if self.no_filter.isChecked():
            self.canvas.display_image(self.cropped_image)
            self.current_display = "cropped"
        else:
            self.canvas.display_image(filtered_image)
            self.current_display = "filtered"

    def update_saturation_label(self):
        # Récupérer la valeur du slider
        value = self.saturation_slider.value()
        self.saturation_slider.setValue(value)
        self.saturation_label.setText(f"Seuil de saturation: {value}%")

    def update_value_label(self):
        # Récupérer la valeur du slider
        value = self.value_slider.value()
        self.value_slider.setValue(value)
        self.value_label.setText(f"Seuil de valeur: {value}%")

    def reset_display(self):
        # Réinitialiser l'affichage à l'image originale
        if self.original_image is not None:
            self.canvas.display_image(self.original_image)
            self.current_display = "original"

            # Réinitialiser les filtres
            self.no_filter.setChecked(True)
            self.filter_group.setEnabled(False)
            self.threshold_group.setEnabled(False)
            
            # Réinitialiser les statistiques
            self.stats_label.setText("Aucune statistique disponible")

            self.circle_selector = CircleSelector(self.canvas, self.handle_selection)
            # Réactiver le bouton de sélection
            # self.select_rect_button.setEnabled(True)

    # def hsv_info(self):
    #     self.load_chosen_image("https://fr.m.wikipedia.org/wiki/Fichier:HSV_color_solid_cylinder_saturation_gray.png")




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Main_window()
    window.show()
    sys.exit(app.exec_())