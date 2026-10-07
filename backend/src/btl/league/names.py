"""Names for clubs and players.

Clubs are named after real English market towns plus an invented nickname. Players get a
real first name and an invented surname in one of several styles, each standing for a part
of the world. First names are common boys' names from official registries or published
frequency lists (see ``docs/name-sources.md``); surnames are built from invented syllables,
so a full name never belongs to a real person on purpose. The style weights roughly follow
the nationalities of a real top-flight English league (see
``docs/milestone-1/implementation-notes.md``).
"""

from collections.abc import Collection
from dataclasses import dataclass

from numpy.random import Generator

# Real English market towns with no professional football club, so a club named after one
# can't be mistaken for a real league side.
TOWNS = (
    "Alnwick", "Bakewell", "Bideford", "Ely", "Helmsley", "Hexham", "Kendal", "Keswick",
    "Ledbury", "Ludlow", "Malton", "Penrith", "Ripon", "Rye", "Sherborne", "Tewkesbury",
    "Thirsk", "Truro", "Wells", "Whitby",
)  # fmt: skip
# Invented club nicknames, avoiding the well-known nicknames of real clubs.
NICKNAMES = (
    "Anchors", "Badgers", "Beacons", "Comets", "Drovers", "Ferrymen", "Kestrels",
    "Kingfishers", "Lanterns", "Larks", "Otters", "Sentinels", "Wardens", "Weavers", "Wyverns",
)  # fmt: skip

VOWELS = frozenset("aeiouyåæéëíóøöú")


@dataclass(frozen=True, slots=True)
class NameStyle:
    """Real first names and invented surname syllables for one style, with its weight."""

    name: str
    weight: float
    first_names: tuple[str, ...]
    surname_starts: tuple[str, ...]
    surname_ends: tuple[str, ...]


NAME_STYLES = (
    NameStyle(
        name="british",
        weight=0.28,
        first_names=(
            "Jack", "Thomas", "James", "Joshua", "Daniel", "Harry", "Samuel", "Joseph", "Matthew",
            "Callum", "Luke", "William", "Lewis", "Oliver", "Ryan", "Benjamin", "George", "Liam",
            "Jordan", "Adam", "Alexander", "Jake", "Connor", "Nathan", "Kieran", "Jamie",
            "Michael", "Ross", "Sean", "Cian",
        ),
        surname_starts=("Ash", "Brax", "Calv", "Corr", "Dray", "Fair", "Gil", "Hart", "Kel", "Lind",
                        "Pen", "Quill", "Rad", "Strat", "Thorn", "Yar"),
        surname_ends=("ard", "by", "holt", "ley", "mere", "ock", "sett", "well", "wick", "win"),
    ),
    NameStyle(
        name="dutch and german",
        weight=0.16,
        first_names=(
            "Lukas", "Jan", "Tim", "Niklas", "Leon", "Jonas", "Finn", "Felix", "Maximilian",
            "Philipp", "Florian", "Tobias", "Christian", "Julian", "Moritz", "Sebastian", "Marcel",
            "Dennis", "Daan", "Thomas", "Lars", "Bram", "Thijs", "Ruben", "Stijn", "Luuk",
            "Jesse", "Niels", "Milan", "Wout",
        ),
        surname_starts=("Berg", "de Wit", "Dek", "Haf", "Kloo", "Lin", "Mei", "Oost", "Ros",
                        "Schel", "van Dor"),
        surname_ends=("emann", "huis", "inga", "kamp", "mer", "ner", "sma", "stra", "ter"),
    ),
    NameStyle(
        name="french",
        weight=0.12,
        first_names=(
            "Thomas", "Nicolas", "Julien", "Quentin", "Maxime", "Alexandre", "Kevin", "Antoine",
            "Romain", "Hugo", "Lucas", "Théo", "Clément", "Florian", "Valentin", "Mathieu",
            "Guillaume", "Pierre", "Adrien", "Baptiste", "Louis", "Enzo", "Mathis", "Nathan",
            "Paul", "Dylan", "Léo", "Corentin", "Jeremy", "Alexis",
        ),
        surname_starts=("Bel", "Chau", "Dela", "Four", "Gir", "Lacro", "Mar", "Rou", "Ver"),
        surname_ends=("ard", "bier", "chet", "deau", "nier", "quet", "selle", "vin"),
    ),
    NameStyle(
        name="portuguese-speaking",
        weight=0.12,
        first_names=(
            "Lucas", "Gabriel", "Matheus", "Felipe", "Bruno", "Rafael", "Guilherme", "Pedro",
            "Gustavo", "Leonardo", "Thiago", "Rodrigo", "João", "Marcos", "Vinícius", "Diego",
            "Daniel", "André", "Leandro", "Eduardo", "Vitor", "Caio", "Igor", "Henrique",
            "Diogo", "Francisco", "Davi", "Samuel", "Miguel", "Arthur",
        ),
        surname_starts=("Al", "Bar", "Car", "Fon", "Lim", "Mar", "Pin", "Sou", "Tei", "Vas"),
        surname_ends=("anhão", "beira", "deiro", "galhães", "queira", "rães", "telo", "teiro",
                      "veira"),
    ),
    NameStyle(
        name="spanish-speaking",
        weight=0.12,
        first_names=(
            "Alejandro", "Daniel", "David", "Javier", "Sergio", "Pablo", "Adrián", "Álvaro",
            "Carlos", "Jorge", "Diego", "Iván", "Rubén", "Miguel", "Luis", "José", "Jesús",
            "Fernando", "Eduardo", "Víctor", "Ángel", "Juan", "Santiago", "Sebastián", "Andrés",
            "Nicolás", "Matías", "Agustín", "Facundo", "Martín",
        ),
        surname_starts=("Alta", "Bal", "Ced", "Esco", "Fer", "Gar", "Mon", "Pal",
                        "Quir", "Rive", "Sar", "Val"),
        surname_ends=("dera", "lano", "mendi", "quez", "rrieta", "ruda", "sende", "vez",
                      "zaga"),
    ),
    NameStyle(
        name="west african",
        weight=0.08,
        first_names=(
            "Ibrahim", "Musa", "Abubakar", "Emmanuel", "Samuel", "Daniel", "David", "Joseph",
            "Yusuf", "Usman", "Umar", "Victor", "Aliyu", "Chinedu", "Emeka", "Kehinde", "Taiwo",
            "Kwame", "Kofi", "Kwabena", "Yaw", "Isaac", "Mamadou", "Moussa", "Ousmane",
            "Abdoulaye", "Ibrahima", "Cheikh", "Seydou", "Adama",
        ),
        surname_starts=("Ade", "Ba", "Danso", "Eke", "Mensa", "Nwa", "Oko", "Tra"),
        surname_ends=("bari", "fo", "gbe", "kunle", "nkwo", "ore", "rafor", "yemi"),
    ),
    NameStyle(
        name="nordic",
        weight=0.06,
        first_names=(
            "Simon", "Alexander", "Erik", "Oscar", "Filip", "Viktor", "Emil", "Anton", "Johan",
            "Marcus", "Sebastian", "Linus", "Hampus", "Albin", "Axel", "Mathias", "Frederik",
            "Mikkel", "Rasmus", "Mads", "Kasper", "Nikolaj", "Jonas", "Andreas", "Magnus",
            "Sondre", "Kristian", "Henrik", "Håkon", "Arnar",
        ),
        surname_starts=("Berg", "Dahl", "Holm", "Lund", "Ny", "Sand", "Strøm", "Vik"),
        surname_ends=("bakk", "gaard", "gren", "heim", "lie", "rud", "stad", "vold"),
    ),
    NameStyle(
        name="slavic",
        weight=0.03,
        first_names=(
            "Jakub", "Kacper", "Mateusz", "Bartosz", "Michał", "Szymon", "Łukasz", "Dawid",
            "Oleksandr", "Andrii", "Dmytro", "Serhii", "Maksym", "Artem", "Bohdan", "Nikola",
            "Stefan", "Marko", "Lazar", "Miloš", "Nemanja", "Đorđe", "Luka", "Ivan", "Josip",
            "Petar", "Tomáš", "Lukáš", "Ondřej", "Vojtěch",
        ),
        surname_starts=("Bre", "Drag", "Jank", "Kova", "Milo", "Nowa", "Pav", "Sto", "Vuk",
                        "Zieli"),
        surname_ends=("czyk", "enko", "čić", "ević", "inov", "ković", "lić", "ski", "šek"),
    ),
    NameStyle(
        name="north african",
        weight=0.03,
        first_names=(
            "Mohamed", "Ahmed", "Youssef", "Omar", "Ali", "Mahmoud", "Mostafa", "Khaled",
            "Karim", "Amr", "Hossam", "Tarek", "Abdelrahman", "Hamza", "Amine", "Ayoub", "Mehdi",
            "Yassine", "Zakaria", "Anas", "Oussama", "Bilal", "Walid", "Sofiane", "Riyad",
            "Ilyes", "Rachid", "Nabil", "Aymen", "Anis",
        ),
        surname_starts=("Ben", "Bou", "Cha", "El", "Ha", "Ka", "Me", "Za"),
        surname_ends=("dani", "hiri", "jid", "kadi", "lal", "mrani", "rouf", "zidi"),
    ),
)  # fmt: skip

_MAX_ATTEMPTS = 1000


def _pick(rng: Generator, options: tuple[str, ...]) -> str:
    return options[int(rng.random() * len(options))]


def join_syllables(start: str, end: str) -> str | None:
    """Join two syllables, or None if the join would clash ("Kel" + "ley", "Ade" + "ore")."""
    if start[-1].lower() == end[0].lower():
        return None
    if start[-1].lower() in VOWELS and end[0].lower() in VOWELS:
        return None
    return start + end


def possible_surnames(style: NameStyle) -> frozenset[str]:
    """Every surname a style can produce."""
    joined = (
        join_syllables(start, end) for start in style.surname_starts for end in style.surname_ends
    )
    return frozenset(name for name in joined if name is not None)


def pick_distinct(rng: Generator, options: tuple[str, ...], count: int) -> tuple[str, ...]:
    """``count`` different items from ``options``, in a random order."""
    if count > len(options):
        raise ValueError(f"can't pick {count} different items from {len(options)}")
    remaining = list(options)
    picked: list[str] = []
    for _ in range(count):
        picked.append(remaining.pop(int(rng.random() * len(remaining))))
    return tuple(picked)


def pick_style(rng: Generator) -> NameStyle:
    """A name style, chosen in proportion to the style weights."""
    draw = rng.random() * sum(style.weight for style in NAME_STYLES)
    for style in NAME_STYLES:
        draw -= style.weight
        if draw < 0:
            return style
    return NAME_STYLES[-1]


def generate_player_name(
    rng: Generator,
    taken_full_names: Collection[str],
    taken_first_names: Collection[str],
    taken_surnames: Collection[str],
) -> tuple[str, str]:
    """A real first name and an invented surname in one style.

    Args:
        rng: The league's random stream.
        taken_full_names: Full names already used anywhere in the league.
        taken_first_names: First names already used in this player's club.
        taken_surnames: Surnames already used in this player's club.

    Returns:
        ``(first_name, last_name)``, e.g. ``("Jack", "Hartwell")`` or ``("João", "Limbeira")``.
    """
    for _ in range(_MAX_ATTEMPTS):
        style = pick_style(rng)
        first = _pick(rng, style.first_names)
        last = join_syllables(_pick(rng, style.surname_starts), _pick(rng, style.surname_ends))
        if last is None or first in taken_first_names or last in taken_surnames:
            continue
        if f"{first} {last}" not in taken_full_names:
            return first, last
    raise RuntimeError("ran out of unused player names")
