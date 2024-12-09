import os
from pdf2docx import Converter
import docx2pdf
from PIL import Image

current_dir = os.getcwd()
file_extension = '.pdf'

def convertdocxtopdf(docxfile, pdffile):
    docx2pdf.convert(docxfile, pdffile)

def delete_files(file_list):
    for file in file_list:
        if os.path.exists(file):
            os.remove(file)
            print(f'{file} удалён.')
        else:
            print(f'{file} не найден.')

while True:
    k = 0
    print('Выберите действие: \n 0. Сменить рабочий каталог \n 1. Преобразовать PDF в Docx \n 2. Преобразовать Docx B PDF \n 3. Произвести сжатие изображений \n 4. Удалить группу файлов \n 5. Выход')
    user_select = input('Ваш выбор: ')

    while int(user_select) not in [0,1,2,3,4,5]:
        print('Введите корректную функции!')
        user_select = input('Ваш выбор: ')
        
    if user_select == '0':
        print(f'\nТекущая рабочая директория: {current_dir} \n')
        path = input('Укажите новый путь к рабочему каталогу: ')
        if os.path.exists(path):
            os.chdir(rf'{path}')
            print(f'Путь {path} существует')
            print(f'Новая рабочая директория: {os.getcwd()}')
        else:
            print(f'Путь {path} не существует \n')

    elif user_select == '1':
        print('Cписок файлов с расширением .pdf:')
        files = [f for f in os.listdir(current_dir) if f.endswith(file_extension)]
        for i, file in enumerate(files, 1):
            print(f'{i}. {file}')

        user_choice = int(input('\nВыберите номер файла, который хотите преобразовать в .docx: ')) - 1
        if user_choice in range(0,len(files)):
            pdf_file = files[user_choice]
            docx_file = pdf_file.replace('.pdf', '.docx')
            cv = Converter(pdf_file)
            cv.convert(docx_file, start=0, end=None)
            cv.close()
            print(f'Файл {pdf_file} успешно преобразован в {docx_file}.')
            os.remove(pdf_file)
        else:
            print('Некорректный выбор.')

    elif user_select == '2':
        print('Cписок файлов с расширением .docx:')
        files = [f for f in os.listdir(current_dir) if f.endswith('.docx')]
        for i, file in enumerate(files, 1):
            print(f'{i}. {file}')
        
        user_choice = int(input('\nВыберите номер файла, который хотите преобразовать в .docx: ')) - 1
        if user_choice in range(0,len(files)):
            docx_file = files[user_choice]
            pdf_file = docx_file.replace('.docx', '.pdf')
            convertdocxtopdf(docx_file, pdf_file)
            print(f'Файл {docx_file} успешно преобразован в {pdf_file}.')
            os.remove(docx_file)
        else:
            print('Некорректный выбор.')

    elif user_select == '3':
        print('Cписок файлов с расширением .png, .jpg, .jpeg:')
        image_extensions = ('.png', '.jpg', '.jpeg')
        files = [f for f in os.listdir(current_dir) if f.endswith(image_extensions)]
        for i, file in enumerate(files, 1):
            print(f'{i}. {file}')
        user_choice = int(input('\nВыберите номер файла, который хотите сжать: ')) - 1
        selected_file = files[user_choice]
        file_path = os.path.join(current_dir, selected_file)

        compress_percentage = int(input('На сколько процентов хотите сжать изображение (введите число от 0 до 100): '))       
        if compress_percentage < 0 or compress_percentage > 100:
            print('Некорректный процент сжатия.')
        else:
            with Image.open(file_path) as img:
                quality = 100 - compress_percentage
                output_file_path = os.path.join(current_dir, f'compressed_{selected_file}')
                img.save(output_file_path, quality=quality)

            print(f"Изображение '{selected_file}' успешно сжато и сохранено как '{output_file_path}'.")


    elif user_select == '4':
        print('Выберите действие: \n 1. Удалить все файлы начинающиеся на определенную подстроку \n 2. Удалить все файлы заканчивающиеся на определенную подстроку \n 3. Удалить все файлы содержащие определенную подстроку \n 4. Удалить все файлы по расширению')
        action_select = input('Ваш выбор: ')
        
        if action_select == '1':
            prefix = input('Введите подстроку, на которую должны начинаться файлы: ')
            files_to_delete = [f for f in os.listdir(current_dir) if f.startswith(prefix)]
            delete_files(files_to_delete)

        elif action_select == '2':
            postfix = input('Введите подстроку, на которую должны заканчиваться файлы: ')
            files_to_delete = [f for f in os.listdir(current_dir) if f.endswith(postfix)]
            delete_files(files_to_delete)

        elif action_select == '3':
            substring = input('Введите подстроку, содержащуюся в файлах: ')
            files_to_delete = [f for f in os.listdir(current_dir) if substring in f]
            delete_files(files_to_delete)

        elif action_select == '4':
            extension = input('Введите расширение файлов, которые нужно удалить (например, .txt): ')
            files_to_delete = [f for f in os.listdir(current_dir) if f.endswith(extension)]
            delete_files(files_to_delete)

        else:
            print('Некорректный выбор')

    else: 
        print('Bыxод из программы') 
        break
