from datetime import date, timedelta


class Book:
    def __init__(self, title, author, isbn, pages):
        self.title = title
        self.author = author
        self.isbn = isbn
        self.pages = pages
        self.available = True

    def borrow(self):
        if not self.available:
            raise ValueError(f"{self.title} is already borrowed")
        self.available = False

    def return_book(self):
        self.available = True

    def describe(self):
        status = "available" if self.available else "borrowed"
        return f"{self.title} by {self.author} ({status})"


class Member:
    LOAN_LIMIT = 5

    def __init__(self, name, member_id):
        self.name = name
        self.member_id = member_id
        self.borrowed = []

    def can_borrow(self):
        return len(self.borrowed) < self.LOAN_LIMIT

    def add_book(self, book):
        if not self.can_borrow():
            raise RuntimeError("Loan limit reached")
        book.borrow()
        self.borrowed.append(book)

    def remove_book(self, book):
        book.return_book()
        self.borrowed.remove(book)

    @property
    def loan_count(self):
        return len(self.borrowed)


class PremiumMember(Member):
    LOAN_LIMIT = 10

    def __init__(self, name, member_id, fee):
        super().__init__(name, member_id)
        self.fee = fee

    def describe(self):
        return f"{self.name} (premium, fee={self.fee})"


class Library:
    def __init__(self, name):
        self.name = name
        self.books = []
        self.members = []

    def add_book(self, book):
        self.books.append(book)

    def register(self, member):
        self.members.append(member)

    def find_by_author(self, author):
        return [b for b in self.books if b.author.lower() == author.lower()]

    def available_count(self):
        return sum(1 for b in self.books if b.available)

    @staticmethod
    def format_catalog(books):
        return "\n".join(b.describe() for b in books)

    @classmethod
    def from_list(cls, name, books):
        lib = cls(name)
        for b in books:
            lib.add_book(b)
        return lib


def calculate_late_fee(book, due_date, daily_rate=0.5):
    days_late = (date.today() - due_date).days
    if days_late <= 0:
        return 0.0
    return round(days_late * daily_rate, 2)


def make_due_date(loan_days=14):
    return date.today() + timedelta(days=loan_days)


def sort_books_by_pages(books, reverse=False):
    return sorted(books, key=lambda b: b.pages, reverse=reverse)


def summarize_library(library):
    total = len(library.books)
    free = library.available_count()
    return {"total": total, "available": free, "borrowed": total - free}


def main():
    lib = Library.from_list("City Library", [
        Book("Dune", "Frank Herbert", "978-0441172719", 412),
        Book("Clean Code", "Robert Martin", "978-0132350884", 464),
        Book("The Pragmatic Programmer", "Andrew Hunt", "978-0135957059", 352),
    ])
    member = PremiumMember("An", "M001", fee=20.0)
    lib.register(member)
    member.add_book(lib.books[0])
    print(summarize_library(lib))
    print(Library.format_catalog(lib.books))


if __name__ == "__main__":
    main()
