from game_components import *
from words import *

print('Это Поле Чудес! Удачной игры!')

word = rand_word()
guessed_letters = set()
record = 0
print('Выберите уровень сложности \n1. Лёгкий уровень: 7 жизней\n2. Средний уровень: 5 жизней.\n3. Сложный уровень: 3 жизни.\n(Напишите 1, 2 или 3) \nВаш выбор: ')
difficult = input()

while difficult.isdigit() == False:
    print('Введите число! Попробуйте еще раз!')
    difficult = input()

cache_difficult = difficult

if difficult == '1':
    attempts = 7
elif difficult == '2':
    attempts = 5
else: attempts = 3

while attempts > 0:
    print('Слово: ', coded(word, guessed_letters=guessed_letters))
    print('Количество жизней: ', live(attempts=attempts))

    letter_choice = input('Введите букву или слово целиком: ').lower()

    if not letter_choice.isalpha():
        print('Пожалуйста, введите букву или слово целиком!')
        continue

    if letter_choice in guessed_letters:
        print('Вы уже использовали эту букву эту букву!')
        continue
    if letter_choice == word:
        print(f'\nПоздравляем! Вы угадали слово {word}! Приз в студию!')
        record += 1
        user_choice = input(f'Ваш рекорд: {record}! \nЖелаете ли вы пойти дальше? \n(Напишите Да или Нет) \nВаш выбор: ').lower()
    
        while user_choice.isalpha() == False:
            print('Введите Да или Нет! Попробуйте еще раз!')
            user_choice = input('Ваш выбор: ').lower()
    
        if user_choice == 'да':
            word = rand_word()
            guessed_letters.clear()
            if cache_difficult == '1':
                attempts = 7
            elif cache_difficult == '2':
                attempts = 5
            else: attempts = 3
        else: 
            with open('record.txt', mode='r', encoding='utf8') as file:
                read = file.read()[-1]
                if int(read) < record:
                    with open('record.txt', mode='w', encoding='utf8') as file:
                        file.write(f'Ваш рекорд: {record}')
            print('Ваш рекорд сохранён/обновлён!')
            break

    guessed_letters.add(letter_choice)

    if letter_choice in word:
        print(f'Вы угадали букву: {letter_choice}! Поздравляем!')
    else:
        print('Неправильно! Попробуйте еще раз!')
        attempts -= 1
    
    if all(letter in guessed_letters for letter in word):
        print(f'\nПоздравляем! Вы угадали слово {word}! Приз в студию!')
        record += 1
        user_choice = input(f'Ваш рекорд: {record}! \nЖелаете ли вы пойти дальше? \n(Напишите Да или Нет) \nВаш выбор: ').lower()
    
        while user_choice.isalpha() == False:
            print('Введите Да или Нет! Попробуйте еще раз!')
            user_choice = input('Ваш выбор: ').lower()
    
        if user_choice == 'да':
            word = rand_word()
            if cache_difficult == '1':
                attempts = 7
            elif cache_difficult == '2':
                attempts = 5
            else: attempts = 3
            guessed_letters.clear()
        else: 
            with open('record.txt', mode='r', encoding='utf8') as file:
                read = file.read()[-1]
                if int(read) < record:
                    with open('record.txt', mode='w', encoding='utf8') as file:
                        file.write(f'Ваш рекорд: {record}')
            print('Ваш рекорд сохранён/обновлён!')
            break

else:
    print(f'\nУ вас не осталось попыток. Загаданное слово было: {word}')