from dataclasses import dataclass, asdict
from urllib import request
from bs4 import BeautifulSoup
import hashlib
import json
import time
import random


@dataclass
class Faq:
    question_hash: str
    question: str
    answer: str


def get_total_pages(soup: BeautifulSoup) -> int:
    all_num_text = soup.select_one(".AllNum").get_text(strip=True)
    total_pages = all_num_text.split("/")[-1]
    return int(total_pages)


def get_faq_from_page(page_num: int) -> list[Faq]:
    url = f"https://www.pokemon-card.com/rules/faq/search.php?ses=1&page={page_num}"
    time.sleep(random.uniform(0.1, 1))
    response = request.urlopen(url)
    soup = BeautifulSoup(response, "html.parser")
    response.close()
    faq_items = soup.select(".FAQResultList_item")
    faq_list: list[Faq] = []
    for i, item in enumerate(faq_items, start=1):
        question = item.select_one(".QuestionArea .BodyArea").get_text(strip=True)
        answer = item.select_one(".AnswerArea .BodyArea").get_text(
            separator="\n", strip=True
        )
        question_hash = hashlib.sha256(question.encode()).hexdigest()
        faq_list.append(
            Faq(question_hash=question_hash, question=question, answer=answer)
        )
    return faq_list


def main():
    url = "https://www.pokemon-card.com/rules/faq/search.php?ses=1&page=1"
    response = request.urlopen(url)

    soup = BeautifulSoup(response, "html.parser")
    response.close()

    all_faq_list: list[Faq] = []

    for i in range(1, get_total_pages(soup=soup) + 1):
        faq_list = get_faq_from_page(i)
        print(faq_list)
        all_faq_list.extend(faq_list)

    sorted_all_faq_list = sorted(all_faq_list, key=lambda faq: faq.question_hash)

    with open("faq_data.json", "w", encoding="utf-8") as json_file:
        json.dump(
            [asdict(faq) for faq in sorted_all_faq_list],
            json_file,
            ensure_ascii=False,
            indent=4,
        )


if __name__ == "__main__":
    main()
