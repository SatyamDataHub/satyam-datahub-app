# Satyam DataHub - Final Version Setup Guide

This guide contains the complete instructions to set up the final, stable version of the application, including full mobile responsiveness and the new wallet/project features.

### **CRITICAL: Fresh Installation Required**

To ensure all new features and bug fixes work correctly, you **MUST DELETE your old `dems.pro` folder** and start fresh with the new files.

### **Step 1: Set Up the Project**

1.  **Create a new `dems_pro` folder.**
2.  Inside it, create the full folder structure (`templates`, `static/css`, `static/images`, `uploads/pending`).
3.  Place all the new, complete `.py`, `.html`, and `.css` files from this guide into their correct locations.
4.  **Add Your Logo**: Place your `logo.png` inside the `static/images/` folder.
5.  **Add Images for Processing**: Place the images for data entry inside the **`uploads/pending/`** folder.

### **Step 2: Best Practices - File Naming**

For best results, make sure your image filenames **do not contain spaces or special characters like `( ) -`**.
* **Bad:** `my image - copy (1).jpg`
* **Good:** `my_image_v1.jpg`

### **Step 3: Setup Virtual Environment & Install Libraries**

1.  Open your terminal in the `dems_pro` folder and activate your virtual environment.
2.  Install all required libraries: `pip install -r requirements.txt`

### **Step 4: Initialize the New Database**

Run the database script to create the new, empty `dems.db` file with the updated structure.
```bash
python database.py