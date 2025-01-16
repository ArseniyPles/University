import os
from pdf2docx import Converter
import docx2pdf
from PIL import Image
import PySimpleGUI as sg

def convertdocxtopdf(docxfile, pdffile):
    docx2pdf.convert(docxfile, pdffile)

def delete_files(file_list):
    for file in file_list:
        if os.path.exists(file):
            os.remove(file)

def compress_image(file_path, output_path, quality):
    with Image.open(file_path) as img:
        img.save(output_path, quality=quality)

layout = [
    [sg.Text("Выберите действие:")],
    [sg.Button("Сменить рабочий каталог"), sg.Text(size=(40, 1), key="-DIR-")],
    [sg.Button("Преобразовать PDF в DOCX")],
    [sg.Button("Преобразовать DOCX в PDF")],
    [sg.Button("Сжать изображения")],
    [sg.Button("Удалить файлы")],
    [sg.Button("Выход")],
]

window = sg.Window("Файловый менеджер", layout)
current_dir = os.getcwd()

while True:
    event, values = window.read()
    if event in (sg.WINDOW_CLOSED, "Выход"):
        break

    if event == "Сменить рабочий каталог":
        new_dir = sg.popup_get_folder("Выберите новый рабочий каталог")
        if new_dir and os.path.exists(new_dir):
            current_dir = new_dir
            window["-DIR-"].update(f"Текущая директория: {current_dir}")
        else:
            sg.popup("Указанный каталог не существует")

    elif event == "Преобразовать PDF в DOCX":
        files = [f for f in os.listdir(current_dir) if f.endswith(".pdf")]
        if not files:
            sg.popup("Нет PDF-файлов в текущей директории")
            continue

        file = sg.popup_get_file("Выберите PDF-файл", file_types=(("PDF Files", "*.pdf"),), initial_folder=current_dir)
        if file:
            output_file = file.replace(".pdf", ".docx")
            cv = Converter(file)
            cv.convert(output_file)
            cv.close()
            sg.popup(f"Файл преобразован в {output_file}")

    elif event == "Преобразовать DOCX в PDF":
        files = [f for f in os.listdir(current_dir) if f.endswith(".docx")]
        if not files:
            sg.popup("Нет DOCX-файлов в текущей директории")
            continue

        file = sg.popup_get_file("Выберите DOCX-файл", file_types=(("DOCX Files", "*.docx"),), initial_folder=current_dir)
        if file:
            output_file = file.replace(".docx", ".pdf")
            convertdocxtopdf(file, output_file)
            sg.popup(f"Файл преобразован в {output_file}")

    elif event == "Сжать изображения":
        files = [f for f in os.listdir(current_dir) if f.endswith((".png", ".jpg", ".jpeg"))]
        if not files:
            sg.popup("Нет изображений в текущей директории")
            continue

        file = sg.popup_get_file("Выберите изображение", file_types=(("Image Files", "*.png;*.jpg;*.jpeg"),), initial_folder=current_dir)
        if file:
            compress_percentage = sg.popup_get_text("Введите степень сжатия (в процентах от 0 до 100)")
            if compress_percentage and compress_percentage.isdigit():
                compress_percentage = int(compress_percentage)
                if 0 <= compress_percentage <= 100:
                    quality = 100 - compress_percentage
                    output_file = os.path.join(current_dir, f"compressed_{os.path.basename(file)}")
                    compress_image(file, output_file, quality)
                    sg.popup(f"Изображение сохранено как {output_file}")
                else:
                    sg.popup("Некорректный процент сжатия")

    elif event == "Удалить файлы":
        files = os.listdir(current_dir)
        selected_files = sg.popup_get_file("Выберите файлы для удаления", multiple_files=True, initial_folder=current_dir)
        if selected_files:
            delete_files(selected_files)
            sg.popup("Файлы удалены")

window.close()