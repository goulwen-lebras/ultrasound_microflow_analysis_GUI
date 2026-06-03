# Ultrasound Microflow Image Analysis Tool

A Python desktop application for analyzing ultrasound images and video sequences, with a focus on quantifying colored microvascular flow signals around venous thrombosis. The application provides an interactive graphical interface to select a circular region of interest (ROI), apply HSV-based color filters, and estimate the proportion of vascular signal inside the selected area.

This tool was developed in the context of ultrasound microvascular flow imaging research, particularly for the evaluation of perithrombotic inflammation and the follow-up of thrombotic episodes.

## Overview

Venous thrombosis is associated with local inflammation, vascular wall remodeling, and perithrombotic microvascularization. Conventional ultrasound is highly effective for diagnosing thrombosis, but it provides limited information about inflammatory activity around the thrombus.

Microvascular flow imaging techniques, such as MV-Flow, can reveal low-velocity microvascular signals surrounding thrombosed veins. Quantifying these signals may help estimate inflammatory activity associated with an acute thrombotic episode and monitor its evolution over time.

This application allows users to:

* Load ultrasound images or ultrasound video files.
* Display and navigate through video frames.
* Select a circular ROI around a thrombosed vein or target area.
* Optionally crop the ROI using twice the selected diameter.
* Apply red-pixel and white-pixel filters.
* Adjust saturation and value thresholds.
* Calculate the percentage of filtered pixels inside the selected ROI.
* Use these measurements as an image-based approximation of vascular signal density.

## Intended Use

The application is intended for research and exploratory analysis of ultrasound microflow images and videos. It may be useful for studying perivenous hyperemia, microvascularization around thrombosis, and image-derived biomarkers such as the vascularity index.

The software is not intended for direct clinical decision-making, diagnosis, prognosis, or treatment guidance without independent clinical validation.

## Scientific Context

Microvascular flow imaging can detect low-velocity blood flow signals that may not be visible using conventional color or power Doppler. In the context of venous thrombosis, perithrombotic hyperemia may reflect inflammatory activity around the thrombus.

The vascularity index can be estimated as the percentage of pixels corresponding to microvascular flow signal within a defined ROI. In longitudinal follow-up, a decrease in vascular signal may reflect regression of inflammatory activity and thrombus evolution.

## Features

### Image Analysis

The application supports loading static ultrasound images in common formats:

* PNG
* JPG / JPEG
* BMP
* TIFF

After loading an image, the user can manually define a circular ROI by clicking and dragging over the displayed image.

### Video Analysis

The application supports loading ultrasound video files in common formats:

* MP4
* AVI
* MOV
* MKV

Video controls include:

* Play
* Pause
* Frame slider
* Frame-by-frame navigation
* Adjustable playback FPS

The current frame can be used for ROI selection and pixel analysis.

### Circular ROI Selection

The user selects a circular ROI by drawing a diameter on the image. The software computes:

* Circle center
* Circle diameter
* Optional crop diameter equal to twice the selected diameter

The selected area is isolated, while pixels outside the ROI are set to black.

### Pixel Filtering

The application provides several filtering modes:

* No filter
* Red filter
* White filter
* Red and white filters combined

Red-pixel detection is performed in HSV color space rather than directly in RGB, because HSV separates chromatic information from brightness. This makes the filter more robust to variations in ultrasound display intensity, gain, and video compression.

The red filter can be adjusted using:

* Saturation threshold
* Value threshold

The white filter detects pixels with high RGB intensity values.

### Statistics

For the selected ROI, the application calculates:

* Number of red pixels
* Percentage of red pixels
* Number of white pixels
* Percentage of white pixels
* Combined filtered pixel percentage

These values can be used as a quantitative approximation of the vascular signal detected within the ROI.

## HSV-Based Filtering

The application uses HSV color filtering to detect red microflow signals in ultrasound images.

!\[HSV color representation](docs/images/HSV\_color\_solid\_cylinder\_saturation\_gray.png)

HSV stands for:

* **Hue**: the dominant color tone, such as red, green, blue, or cyan.
* **Saturation**: the intensity or purity of the color.
* **Value**: the brightness of the pixel.

In this application, red signal is detected by converting the image from RGB to HSV and selecting pixels whose hue corresponds to red, while also applying minimum saturation and value thresholds.

### Why HSV Filtering Instead of RGB?

HSV filtering is preferred over direct RGB thresholding because it separates color information from brightness information.

In RGB images, the red signal is represented by a combination of red, green, and blue channel intensities. A pixel may appear red under one brightness condition but fail a fixed RGB threshold under another condition. Ultrasound screenshots and videos often contain variable brightness, compression artifacts, overlays, gain differences, and local contrast variations. These variations make simple RGB thresholds less robust.

HSV is more suitable for this application because:

* **Hue** allows the software to target red independently of brightness.
* **Saturation** helps exclude gray or weakly colored pixels that are unlikely to represent true color-flow signal.
* **Value** allows dark pixels or low-intensity noise to be rejected.
* Thresholds are easier to interpret and adjust manually.
* The method is more stable when image brightness varies between frames or acquisitions.

For this reason, the application detects red microflow pixels using hue ranges corresponding to red, combined with adjustable saturation and value thresholds. This approach provides a more flexible and reproducible estimation of colored vascular signal than fixed RGB thresholds.

## RGB to HSV Conversion

Images loaded by the application are initially represented in RGB format. In RGB, each pixel is described by three intensity values:

* **R**: red channel
* **G**: green channel
* **B**: blue channel

Each value usually ranges from 0 to 255.

For color-based filtering, the application converts RGB images to HSV color space.

HSV represents each pixel using:

* **H — Hue**: the color type, such as red, yellow, green, cyan, blue, or magenta.
* **S — Saturation**: the color intensity or purity.
* **V — Value**: the brightness of the pixel.

This conversion makes it easier to isolate red ultrasound microflow signals, because red can be selected mainly using the hue component, while saturation and value thresholds help remove gray pixels, dark pixels, and background noise.

### Conversion Principle

Given a pixel with RGB values normalized between 0 and 1:

```text
R' = R / 255
G' = G / 255
B' = B / 255
```

The maximum and minimum channel values are computed:

```text
Cmax = max(R', G', B')
Cmin = min(R', G', B')
Delta = Cmax - Cmin
```

The **Value** component is:

```text
V = Cmax
```

The **Saturation** component is:

```text
S = 0                  if Cmax = 0
S = Delta / Cmax       otherwise
```

The **Hue** component depends on which RGB channel has the maximum value:

```text
H = 0                                  if Delta = 0
H = 60 × (((G' - B') / Delta) mod 6)   if Cmax = R'
H = 60 × (((B' - R') / Delta) + 2)     if Cmax = G'
H = 60 × (((R' - G') / Delta) + 4)     if Cmax = B'
```

Hue is usually expressed in degrees from 0° to 360°.

In Python, `skimage.color.rgb2hsv()` returns HSV values normalized between 0 and 1:

```python
from skimage import color

hsv\_image = color.rgb2hsv(rgb\_image)

hue = hsv\_image\[:, :, 0]
saturation = hsv\_image\[:, :, 1]
value = hsv\_image\[:, :, 2]
```

In this application, red pixels are detected using two hue intervals, because red is located around both ends of the hue circle:

```python
lower\_red1, upper\_red1 = 0.0, 0.1
lower\_red2, upper\_red2 = 0.8, 1.0
```

The red mask is then combined with saturation and value thresholds:

```python
mask1 = (
    (hue >= lower\_red1) \& (hue <= upper\_red1) \&
    (saturation >= saturation\_threshold) \&
    (value >= value\_threshold)
)

mask2 = (
    (hue >= lower\_red2) \& (hue <= upper\_red2) \&
    (saturation >= saturation\_threshold) \&
    (value >= value\_threshold)
)

mask\_red = mask1 | mask2
```

This allows the application to detect red microflow pixels while excluding dark, gray, or weakly colored pixels.

### Difference Between Saturation and Value

In HSV color space, **Saturation** and **Value** describe two different properties of a pixel.

**Saturation** measures how pure or intense the color is. A highly saturated pixel has a vivid color, while a low-saturation pixel appears grayish, pale, or close to white or black.

**Value** measures the brightness of the pixel. A high-value pixel is bright, while a low-value pixel is dark.

In this application, saturation and value thresholds are used together to improve red microflow detection:

* The saturation threshold removes weakly colored or gray pixels.
* The value threshold removes dark pixels and low-intensity noise.

This helps preserve bright, clearly colored red flow signals while excluding background pixels, shadows, and grayscale ultrasound structures.

## Installation

### Requirements

The application requires Python 3 and the following packages:

```bash
pip install numpy matplotlib PyQt5 imageio scikit-image
```

A possible `requirements.txt` file is:

```text
numpy
matplotlib
PyQt5
imageio
scikit-image
```

## Usage

Run the application with:

```bash
python main.py
```

### Basic Workflow

1. Open the application.
2. Load an ultrasound image or video.
3. For video files, navigate to the frame of interest.
4. Draw a circular ROI around the thrombosed vein or target area.
5. Choose the desired filter:

   * red signal
   * white signal
   * red and white signal
6. Adjust the saturation and value thresholds if needed.
7. Read the pixel statistics displayed in the interface.
8. Record the percentage value for follow-up or research analysis.

## Suggested Analysis Protocol

For reproducible measurements, it is recommended to:

1. Use the same ultrasound acquisition settings across examinations.
2. Use the same MV-Flow or microflow imaging preset.
3. Keep gain and display settings constant when comparing time points.
4. Select a comparable anatomical plane during follow-up.
5. Use a standardized circular ROI around the thrombosed vein.
6. Apply identical threshold settings for all measurements in the same patient or study.
7. Report the filtered pixel percentage as an image-derived vascularity estimate.

## Example Application

In a follow-up study of superficial venous thrombosis, this tool may be used to quantify perithrombotic microvascularization at different time points:

* Baseline
* 1 month
* 3 months
* 6 months

A progressive decrease in vascular signal percentage may suggest a reduction in perithrombotic inflammatory activity.

## Project Structure

```text
.
├── main.py
├── README.md
├── requirements.txt
└── docs/
    └── images/
        └── HSV\_color\_solid\_cylinder\_saturation\_gray.png
```

## Limitations

This software performs color-based pixel quantification and does not automatically distinguish true vascular flow from all possible imaging artifacts. Results depend on image quality, acquisition settings, display parameters, ROI selection, and threshold values.

The current version uses manual ROI selection and simple pixel-based filtering. Further validation is required before using the measurements as a standardized clinical biomarker.

## Future Improvements

Possible future developments include:

* Export of measurements to CSV.
* Automatic saving of analyzed frames.
* Batch analysis of video sequences.
* Semi-automatic vessel or thrombus segmentation.
* Standardized vascularity index calculation.
* Improved artifact rejection.
* Support for DICOM ultrasound files.
* Inter-operator reproducibility tools.
* Longitudinal patient follow-up module.

## Disclaimer

This application is a research tool. It is not a certified medical device and must not be used as the sole basis for diagnosis, prognosis, or therapeutic decision-making. All results should be interpreted by qualified healthcare professionals and validated within an appropriate clinical or research framework.

## Authors

Developed as part of a research project on ultrasound microvascular imaging and thrombosis-associated inflammation.

