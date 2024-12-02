import re
import csv
import ssl
import urllib.request

url = "https://msk.spravker.ru/avtoservisy-avtotehcentry/"
response = urllib.request.urlopen(url)
html_content = response.read().decode()

with open('html.txt', mode='w', encoding='utf8') as file:
    file.write(html_content)

pattern = r'class="org-widget-header__title-link">([^<]+)</a>.*?' \
          r'org-widget-header__meta--location">([^<]+)</span>.*?' \
          r'<dt class="spec__index"><span class="spec__index-inner">Телефон</span></dt>.*?' \
          r'<dd class="spec__value">([^<]+)</dd>.*?' \
          r'<dt class="spec__index"><span class="spec__index-inner">Часы работы</span></dt>.*?' \
          r'<dd class="spec__value">([^<]+)</dd>'

matches = re.findall(pattern, html_content, re.DOTALL)


with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)

    writer.writerow(['Наименование', 'Адрес', 'Телефон', 'Часы работы'])
    writer.writerows(matches)