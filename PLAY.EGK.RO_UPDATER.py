import os
import customtkinter as ctk
from tkinter import messagebox
import requests
import zipfile
import shutil
import tempfile
import psutil
import sys
import threading

APPDATA = os.getenv('APPDATA')
MC_FOLDER = os.path.join(APPDATA, ".minecraft")
MC_VERSIONS = os.path.join(MC_FOLDER, "versions")
MODS_FOLDER = os.path.join(MC_VERSIONS, "PLAY.EGK.RO", "mods")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

progress_bar = None
status_label = None
app_window = None

def is_tlauncher_installed():
    return os.path.exists(os.path.join(MC_FOLDER, "TLauncher.exe")) or \
           os.path.exists(os.path.join(MC_FOLDER, "TLauncherProfiles.json"))

def check_tlauncher_with_continue():
    if not is_tlauncher_installed():
        result = messagebox.askyesno("Atentie", "TLauncher nu a fost detectat!\nVrei sa continui oricum?")
        if not result:
            sys.exit()

def is_minecraft_running_safe():
    for proc in psutil.process_iter(['name', 'cmdline']):
        if proc.info['name'] == "javaw.exe":
            if any("minecraft" in str(arg).lower() for arg in proc.info['cmdline']):
                return True
    return False

def check_minecraft_running_with_continue():
    if is_minecraft_running_safe():
        result = messagebox.askyesno("Minecraft Deschis", "Minecraft pare sa fie deschis.\nVrei sa continui oricum?")
        if not result:
            sys.exit()

def get_latest_zip_url():
    response = requests.get("https://api.github.com/repos/Eug3nK/MODSEGK/releases/latest")
    response.raise_for_status()
    for asset in response.json().get("assets", []):
        if asset['name'] == "PLAY.EGK.RO.zip":
            return asset['browser_download_url']
    raise Exception("PLAY.EGK.RO.zip nu a fost gasit.")

def get_latest_egk_core_url():
    response = requests.get("https://api.github.com/repos/Eug3nK/egkcore/releases/latest")
    response.raise_for_status()
    for asset in response.json().get("assets", []):
        if asset['name'].startswith("EGK-Core") and asset['name'].endswith(".jar"):
            return asset['browser_download_url']
    raise Exception("EGK-Core nu a fost gasit.")

def download_file(url, dest_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    total = int(response.headers.get('content-length', 0))
    downloaded = 0
    chunk_size = 8192
    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size):
            f.write(chunk)
            downloaded += len(chunk)
            update_progress_bar(downloaded, total)

def update_progress_bar(current, total):
    if progress_bar and app_window:
        app_window.after(10, lambda: progress_bar.set(current / total))

def install_modsegk():
    check_tlauncher_with_continue()
    check_minecraft_running_with_continue()
    try:
        play_folder = os.path.join(MC_VERSIONS, "PLAY.EGK.RO")
        if os.path.exists(play_folder):
            shutil.rmtree(play_folder)
        os.makedirs(play_folder, exist_ok=True)

        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "modsegk.zip")

        update_status("Se descarca modpack-ul...")
        download_file(get_latest_zip_url(), zip_path)

        update_status("Se dezarhiveaza...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(play_folder)

        os.remove(zip_path)
        shutil.rmtree(temp_dir)

        if os.path.exists(os.path.join(play_folder, "mods")):
            messagebox.showinfo("Succes", "Modpack-ul complet a fost instalat!")
        else:
            messagebox.showwarning("Atentie", "Modpack-ul a fost instalat dar folderul mods nu a fost gasit!")

        update_status("Gata")
    except Exception as e:
        messagebox.showerror("Eroare", f"A aparut o eroare: {e}")
        update_status("Eroare")

def verifica_mods():
    check_tlauncher_with_continue()
    check_minecraft_running_with_continue()
    try:
        os.makedirs(MODS_FOLDER, exist_ok=True)

        # Sterge toate versiunile EGK-Core*.jar
        for file in os.listdir(MODS_FOLDER):
            if file.startswith("EGK-Core") and file.endswith(".jar"):
                os.remove(os.path.join(MODS_FOLDER, file))

        update_status("Se descarca EGK-Core...")
        latest_url = get_latest_egk_core_url()
        jar_path = os.path.join(MODS_FOLDER, os.path.basename(latest_url))
        download_file(latest_url, jar_path)

        messagebox.showinfo("Succes", "EGK-Core a fost actualizat!")
        update_status("Gata")
    except Exception as e:
        messagebox.showerror("Eroare", f"A aparut o eroare: {e}")
        update_status("Eroare")

def create_tooltip(widget, text):
    tooltip = ctk.CTkToplevel()
    tooltip.withdraw()
    tooltip.overrideredirect(True)
    label = ctk.CTkLabel(tooltip, text=text, fg_color="black", text_color="white", corner_radius=4, padx=6, pady=3)
    label.pack()
    widget.bind("<Enter>", lambda e: (tooltip.geometry(f"+{e.x_root+10}+{e.y_root+10}"), tooltip.deiconify()))
    widget.bind("<Leave>", lambda e: tooltip.withdraw())

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def update_status(text):
    if status_label and app_window:
        app_window.after(10, lambda: status_label.configure(text=text))

def run_in_thread(func):
    threading.Thread(target=func, daemon=True).start()

def create_gui():
    global progress_bar, status_label, app_window

    app_window = ctk.CTk()
    app_window.geometry("600x450")
    app_window.title("PLAY.EGK.RO Updater")
    app_window.iconbitmap(resource_path("egk.ico"))
    app_window.resizable(False, False)
    app_window.configure(fg_color="#f4e9d8")

    from PIL import Image
    background_image = Image.open(resource_path("background.png"))
    bg_ctk = ctk.CTkImage(light_image=background_image, dark_image=background_image, size=(600, 450))
    ctk.CTkLabel(master=app_window, image=bg_ctk, text="").place(x=0, y=0, relwidth=1, relheight=1)

    install_btn = ctk.CTkButton(app_window, text="Install Mod Complet", command=lambda: run_in_thread(install_modsegk),
                                 corner_radius=0, width=400, height=80, font=("Arial", 22, "bold"),
                                 text_color="#1a1a1a", fg_color="#f4e9d8", hover_color="#e0d5c3", border_width=0)
    install_btn.place(relx=0.5, y=250, anchor="center")

    update_btn = ctk.CTkButton(app_window, text="Update EGK Core", command=lambda: run_in_thread(verifica_mods),
                                corner_radius=0, width=400, height=80, font=("Arial", 22, "bold"),
                                text_color="#1a1a1a", fg_color="#f4e9d8", hover_color="#e0d5c3", border_width=0)
    update_btn.place(relx=0.5, y=340, anchor="center")

    progress_bar = ctk.CTkProgressBar(app_window, width=400, height=20,
                                      progress_color="#c09050", fg_color="#bba980", corner_radius=0)
    progress_bar.place(relx=0.5, y=395, anchor="center")
    progress_bar.set(0)

    status_label = ctk.CTkLabel(app_window, text="", font=("Arial", 18, "bold"),
                                 text_color="#1a1a1a", fg_color="transparent")
    status_label.place(relx=0.5, y=425, anchor="center")

    create_tooltip(install_btn, "Instaleaza toate fisierele modpack-ului complet.")
    create_tooltip(update_btn, "Actualizeaza ultima versiune EGK-Core automat.")
    app_window.mainloop()

if __name__ == "__main__":
    create_gui()
