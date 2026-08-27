"""Site copy, in both languages.

The source of record is ``uploads/kmq_content.docx`` from the Claude Design
project — "KMQ — كي إم كيو لخدمات حماية وتظليل السيارات, محتوى الموقع
الإلكتروني, أغسطس 2026". Where the design file and the Word document disagree,
the Word document wins; every such case is listed in docs/DESIGN-IMPORT.md.

Two rules hold throughout:

* ``AR`` and ``EN`` carry identical key sets, and identically-shaped records.
  ``test_content.py`` asserts it.
* Anything the Word document's "Pending Items" section lists as undecided is
  ``TBD``. It is never a plausible-looking placeholder. The document leaves
  branch phone numbers, addresses, hours and two prices open, and the design
  file filled them with invented values; those values are not here.
"""

from __future__ import annotations

from typing import Any


class _Tbd:
    """A fact the client has not supplied yet.

    Falsy, so ``{% if branch.phone %}`` does the right thing, and templates
    that want to print it call ``t.tbd`` for the localised wording rather
    than rendering the sentinel.
    """

    __slots__ = ()

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "TBD"


TBD = _Tbd()


# --------------------------------------------------------------------------
# Icons. Path data lifted verbatim from the design file's ICONS constant.
# --------------------------------------------------------------------------

ICONS = {
    "shield": "M12 3l7 2.6v5.6c0 4.6-3 7.8-7 9.8-4-2-7-5.2-7-9.8V5.6z M9 12l2.2 2.2L15.4 10",
    "blade": "M3.5 20.5l6.5-6.5 M10 14l3.6-10.5 6.9 6.9L10 14z",
    "pin": "M12 21.5s6.8-6.2 6.8-11.6a6.8 6.8 0 10-13.6 0C5.2 15.3 12 21.5 12 21.5z M12 11.6a1.9 1.9 0 100-3.8 1.9 1.9 0 000 3.8z",
    "chat": "M20 4.5H4v11.5h4.5V20l4.6-3.9H20z M8.5 10.2h7",
    "shieldLine": "M12 3l7 2.6v5.6c0 4.6-3 7.8-7 9.8-4-2-7-5.2-7-9.8V5.6z M12 8.4v7.2",
    "droplet": "M12 20.5c3.4 0 6-2.5 6-5.7C18 10.5 12 3.5 12 3.5S6 10.5 6 14.8c0 3.2 2.6 5.7 6 5.7z M9.6 14.9c0 1.4 1.1 2.5 2.4 2.5",
    "sun": "M12 6.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11z M12 2v2.2 M12 19.8V22 M2 12h2.2 M19.8 12H22 M5 5l1.6 1.6 M17.4 17.4L19 19 M19 5l-1.6 1.6 M6.6 17.4L5 19",
    "roller": "M8 20.5H4.5v-3.4L15.6 6l3.4 3.4z M13.4 8.2l3.4 3.4",
    "frontKit": "M2.8 14.6h18.4 M4.6 14.6l1.8-5.1a2 2 0 011.9-1.3h7.4a2 2 0 011.9 1.3l1.8 5.1 M4.6 14.6v3.2h14.8v-3.2 M7.2 17.8v1.7 M16.8 17.8v1.7 M9 8.2v6.4",
    "truck": "M2.8 7.6h9.6v9.2H2.8z M12.4 11h4l3 3v2.8h-7 M6.4 20a1.8 1.8 0 100-3.6 1.8 1.8 0 000 3.6z M16.6 20a1.8 1.8 0 100-3.6 1.8 1.8 0 000 3.6z",
    "card": "M3 6.6h18v10.8H3z M3 10.4h18 M6.6 14.2h3.4",
    "tick": "M5 12.5l4.5 4.5L19 7.5",
}


# --------------------------------------------------------------------------
# Stable identifiers. Slugs are the same in both languages — the Word
# document's sitemap specifies English slugs and the SEO table targets them.
# --------------------------------------------------------------------------

SERVICE_SLUGS = ("ppf-gloss", "ppf-matte", "nano-ceramic", "window-tint", "colour-change")
PACKAGE_SLUGS = ("gloss", "matte", "colour-change", "nano-ceramic", "window-tint",
                 "front-kit", "quarter-front", "combo")
BRANCH_IDS = ("al-rimal", "al-hamra", "tuwaiq", "jeddah-madinah-road", "dammam-al-manar", "dammam-imam")
CATEGORY_SLUGS = ("guides", "comparisons", "pricing", "care", "tinting")

#: The line KMQ answers on. One number for the call button, for every branch
#: card and for the WhatsApp links, so a change lands everywhere at once.
#: E.164 for tel: and for wa.me, spaced for reading.
PHONE_PRIMARY = "+966 56 402 9777"
PHONE_PRIMARY_E164 = "+966564029777"

#: City label shown above each branch name. Latin in both locales, as in the
#: design source. Al Rimal carries the head-branch suffix: the client's note
#: made it the main branch, and the label is where that reads without a new
#: component.
BRANCH_CITY_EN = ("RIYADH · MAIN BRANCH", "RIYADH", "RIYADH", "JEDDAH", "DAMMAM", "DAMMAM")

#: Which package the "most chosen" flag sits on. Gloss, per the design.
FEATURED_PACKAGE = "gloss"

#: The packages the home page shows, in order. The design file's homeOrder was
#: [gloss, matte, window tint]; the three partial packages follow it, so the
#: full-body ones still lead and the row fills to two of three.
HOME_PACKAGES = ("gloss", "matte", "window-tint",
                 "front-kit", "quarter-front", "combo")


def _svc(slug: str, name: str, tagline: str, icon: str, lede: str,
         points: list[str], warranty: str, alt: str = "") -> dict[str, Any]:
    # The photograph is named after the slug, the way the blog's already are,
    # so adding one is a file in static/img/services/ and nothing here.
    # `alt` describes the work in the frame and so is written per locale.
    return {
        "slug": slug, "name": name, "tagline": tagline, "icon": icon,
        "lede": lede, "points": points, "warranty": warranty,
        "image": f"img/services/{slug}", "alt": alt,
    }


def _pkg(slug: str, name: str, includes: str, price: Any, warranty: str) -> dict[str, Any]:
    return {
        "slug": slug, "name": name, "includes": includes, "price": price,
        "warranty": warranty, "featured": slug == FEATURED_PACKAGE,
    }


#: The five storefront photographs the client supplied, in the order the
#: branches are listed. There is no sixth, and the client's decision was that
#: Al-Manar keeps the entrance shot the whole grid used to share rather than
#: repeat one of the five — so the absence is recorded here, not papered over.
_BRANCH_PHOTOS = {
    "al-rimal": "img/branches/al-rimal",
    "al-hamra": "img/branches/al-hamra",
    "tuwaiq": "img/branches/tuwaiq",
    "jeddah-madinah-road": "img/branches/jeddah-madinah-road",
    "dammam-imam": "img/branches/dammam-imam",
}


def _branch(bid: str, name: str, city: str, location: str, short: str,
            city_en: str) -> dict[str, Any]:
    # phone, hours and address are TBD for every branch: the Word document's
    # pending list asks the client for them and supplies none.
    return {
        "id": bid, "name": name, "city": city, "location": location,
        "short": short, "city_en": city_en,
        "phone": TBD, "hours": TBD, "map_url": TBD,
        # A stem when the branch has its own photograph, None when it falls
        # back to the shared entrance shot. Templates branch on this.
        "image": _BRANCH_PHOTOS.get(bid),
    }


def _post(slug: str, title: str, excerpt: str, category: str, date: str,
          minutes: int, author: str) -> dict[str, Any]:
    # Every article ships with one photograph, named after its slug and shared
    # by both locales: the subject is the same car, only the caption changes.
    return {
        "slug": slug, "title": title, "excerpt": excerpt, "category": category,
        "date": date, "minutes": minutes, "author": author,
        "image": f"img/blog/{slug}.jpg",
    }


# ==========================================================================
# Arabic — the document's Part One, verbatim.
# ==========================================================================

AR: dict[str, Any] = {
    "lang": "ar",
    "dir": "rtl",
    "other_lang": "en",
    "other_label": "EN",
    "locale_name": "العربية",

    "brand_tagline": "كي إم كيو لخدمات حماية وتظليل السيارات",
    "tbd": "يُحدَّد لاحقًا",

    # ---- Global calls to action ----
    "cta_book": "احجز فحص مجاني",
    "cta_whatsapp": "تواصل على واتساب",
    "cta_contact": "تواصل معنا",
    "learn_more": "اعرف أكثر ←",

    # ---- Navigation. Order and labels from the document's sitemap. ----
    "nav": [
        {"key": "home", "label": "الرئيسية"},
        {"key": "about", "label": "من نحن"},
        {"key": "services", "label": "خدماتنا"},
        {"key": "packages", "label": "باقاتنا"},
        {"key": "warranty", "label": "الضمان"},
        {"key": "branches", "label": "الفروع"},
        {"key": "blog", "label": "المدونة"},
        {"key": "contact", "label": "تواصل معنا"},
    ],

    # ---- WhatsApp message templates ----
    "wa_default": "مرحبًا، أرغب بمعرفة تفاصيل خدمات KMQ",
    "wa_order": "مرحبًا، أرغب بطلب ",
    "wa_book": "مرحبًا، أرغب بالحجز في ",
    "wa_contact": "مرحبًا KMQ، عندي استفسار عن حماية سيارتي وأرغب بالتواصل مع أحد المختصين",
    "phone_primary": PHONE_PRIMARY,
    "phone_primary_e164": PHONE_PRIMARY_E164,
    "call_us": "اتصل بنا",
    "wa_pickup": "مرحبًا، أرغب بطلب خدمة الاستلام والتوصيل",

    # ---- Home: hero ----
    "hero_kicker": "PPF · CERAMIC · TINT · WRAP",
    "hero_a": "بيت حماية احترافي",
    "hero_b": "لسيارتك الفاخرة",
    "hero_sub": "تسعير واضح من أول رسالة، وتركيب دقيق باحترافية عالية — في الرياض وجدة والدمام",
    "hero_cta1": "احجز فحص مجاني الآن على واتساب",
    "hero_cta2": "شاهد باقاتنا",
    "hero_shot": "[ hero image: PPF film being applied — dramatic side light, black Porsche ]",

    # ---- Home: hero protection stack ----
    # Scroll-driven build-up. The four rows are the four scroll stages, in
    # order; "code" is the rail label and stays Latin in both locales.
    "stack_kicker": "00 — PROTECTION STACK",
    "stack": [
        {"code": "01 BARE PAINT",   "a": "سيارتك كما",  "b": "خرجت من المصنع",
         "body": "الطلاء الأصلي بلا حماية. مرّر للأسفل لترى الطبقات الثلاث التي نضيفها."},
        {"code": "02 PPF FILM",     "a": "فيلم الحماية", "b": "PPF",
         "body": "طبقة شفافة ذاتية الالتئام تمتص الخدوش وحصى الطريق قبل أن تصل إلى الطلاء."},
        {"code": "03 THERMAL TINT", "a": "التظليل",      "b": "الحراري",
         "body": "يحجب الأشعة فوق البنفسجية ويخفض حرارة المقصورة، بمواصفات مطابقة للنظام السعودي."},
        {"code": "04 CERAMIC COAT", "a": "العازل",       "b": "السيراميكي",
         "body": "لمعان زجاجي يصدّ الماء والأتربة، ويجعل الغسيل أسرع والسيارة أنظف لوقت أطول."},
    ],
    "stack_shot": "سيارة دفع رباعي من زاوية أمامية جانبية",

    # ---- Home: trust strip ----
    "trust": [
        {"title": "ضمان يصل إلى 10 سنوات", "meta": "UP TO 10 YEARS", "icon": ICONS["shield"]},
        {"title": "دقة تركيب يدوي احترافي", "meta": "HAND-CUT PRECISION", "icon": ICONS["blade"]},
        {"title": "6 فروع — الرياض وجدة والدمام", "meta": "3 CITIES · 6 BRANCHES", "icon": ICONS["pin"]},
        {"title": "رد فوري على واتساب", "meta": "REPLY IN MINUTES", "icon": ICONS["chat"]},
    ],

    # ---- Services ----
    "services_title": "خدمات حماية وتجميل شاملة لسيارتك",
    "services_page_title": "خدماتنا — حماية وتجميل بمعايير واضحة",
    "services_page_sub": "خمس خدمات، لكل واحدة مواصفات وضمان معلن. اختر ما يناسب سيارتك وميزانيتك.",
    "services": [
        _svc(
            "ppf-gloss", "حماية PPF لامع", "الحماية الهيكلية الحقيقية لطلاء سيارتك من الخدوش والحصى.",
            ICONS["shieldLine"],
            "فيلم حماية شفاف بسماكة 7.5 مللي يحمي طلاء سيارتك من الخدوش اليومية والحصى، بلمعان يبرز لون الوكالة الأصلي.",
            [
                "مقاومة عالية للخدوش اليومية",
                "معالجة ذاتية للخدوش البسيطة (Self Healing)",
                "ضمان 10 سنوات — التفاصيل الكاملة في صفحة الضمان",
                "تركيب يدوي دقيق، مع خيار القص بالليزر عند الطلب",
            ],
            "10 سنوات",
            "فني يمرّر المكشطة على فيلم حماية شفاف فوق غطاء محرك سيارة سيدان رمادية",
        ),
        _svc(
            "ppf-matte", "حماية PPF مطفي", "تمايز جمالي بدقة تركيب عالية.",
            ICONS["shieldLine"],
            "فيلم حماية بلمسة نهائية غير لامعة يمنح السيارة مظهرًا مختلفًا عن طلاء الوكالة الأصلي، مع نفس مستوى الحماية الهيكلية.",
            [
                "مظهر جمالي فريد يميّز سيارتك",
                "مقاوم للحرارة",
                "ضمان 7 سنوات — التفاصيل الكاملة في صفحة الضمان",
                "تركيب يدوي دقيق، مع خيار القص بالليزر عند الطلب",
            ],
            "7 سنوات",
            "فني بزي KMQ يثبّت حافة فيلم الحماية المطفي على غطاء محرك بورش سوداء مطفية",
        ),
        _svc(
            "nano-ceramic", "نانو سيراميك", "لمعان استثنائي بديل اقتصادي.",
            ICONS["droplet"],
            "النانو سيراميك بديل أوفر للـ PPF، لكنه ليس بنفس مستوى الحماية. هو طبقة كيميائية رقيقة تحسّن اللمعان وتقاوم الأتربة والماء، لكنها لا تمنع الخدوش أو الحصى مثل فيلم الـ PPF السميك.",
            [
                "لمعان يتجاوز 75% (كطبقة إضافية مع PPF أو بشكل مستقل)",
                "مقاومة للأتربة والماء (خاصية هيدروفوبيك)",
                "خيار اقتصادي مناسب لميزانية أقل",
                "حل تجميلي — وليس بديلًا هيكليًا كاملًا عن PPF",
            ],
            "سنتان",
            "يد بقفاز تفرد النانو سيراميك بقطعة ميكروفايبر على غطاء محرك أسود لامع، وقطرات الماء تتجمّع على السطح",
        ),
        _svc(
            "window-tint", "تظليل عازل حراري", "راحة داخل السيارة من أول يوم.",
            ICONS["sun"],
            "عازل حراري يقلل من دخول الحرارة والأشعة داخل السيارة.",
            [
                "تقليل الحرارة داخل المقصورة",
                "حماية من الأشعة فوق البنفسجية",
                "درجات تظليل متعددة حسب الأنظمة المسموحة",
                "سعر دخول تنافسي",
            ],
            "10 سنوات",
            "سائق جالس مرتاحًا داخل سيارة زرقاء تحت شمس قوية، وأشعة الحرارة ترتد عن الزجاج بينما الهواء داخل المقصورة بارد",
        ),
        _svc(
            "colour-change", "تغيير اللون", "أعد تعريف شكل سيارتك بالكامل.",
            ICONS["roller"],
            "تغيير لون كامل الهيكل الخارجي بأي لون تختاره، بجودة تركيب احترافية وضمان يصل إلى 7 سنوات.",
            [
                "اختيار حر بين عشرات الألوان والتشطيبات",
                "مدة تنفيذ تقريبية: 10 إلى 15 يومًا",
                "ضمان 7 سنوات",
                "إمكانية دمجها مع حماية PPF ملوّنة",
            ],
            "7 سنوات",
            "يد بقفاز أزرق تحمل مروحة عيّنات ألوان أمام سيارة داكنة",
        ),
    ],

    # ---- Packages ----
    "packages_title": "باقات واضحة، أسعار ثابتة، بدون تفاوض",
    "packages_page_title": "باقات واضحة، أسعار ثابتة — اختر ما يناسب سيارتك",
    "most_chosen": "الأكثر اختيارًا",
    "sar": "ريال سعودي",
    "warranty_label": "الضمان",
    "order_package": "اطلب هذه الباقة",
    "order_on_whatsapp": "اطلب هذه الباقة على واتساب",
    "all_packages_link": "كل تفاصيل الباقات والإضافات ←",
    "packages": [
        _pkg("gloss", "باقة الحماية اللامعة",
             "PPF لامع لكامل السيارة + نانو سيراميك + خدمات إضافية مجانية",
             "6,000 – 7,500", "10 سنوات"),
        _pkg("matte", "باقة الحماية المطفية",
             "PPF مطفي لكامل السيارة + نانو سيراميك + خدمات إضافية مجانية",
             "7,000 – 8,000", "7 سنوات"),
        _pkg("colour-change", "باقة تغيير اللون",
             "تغيير لون كامل الهيكل الخارجي بفيلم PPF ملوّن، بأي لون تختاره",
             "8,500 – 12,500", "7 سنوات"),
        _pkg("nano-ceramic", "باقة النانو سيراميك",
             "طبقة نانو سيراميك كاملة للبدي",
             "1,100 – 1,650", "حسب نوع الطبقة"),
        # Ten years on the tint and on the three partial packages: the client
        # confirmed the term for all four together. It matches the tint
        # warranty block on the warranty page, which already said ten.
        _pkg("window-tint", "باقة العازل الحراري",
             "تظليل عازل حراري كامل السيارة",
             "700 – 900", "10 سنوات"),
        _pkg("front-kit", "باقة الوجهية",
             "PPF للواجهة الأمامية",
             "2,200 – 2,700", "10 سنوات"),
        _pkg("quarter-front", "باقة الربع",
             "PPF لربع الواجهة الأمامية",
             "1,100 – 1,450", "10 سنوات"),
        _pkg("combo", "باقة الكومبو",
             "الوجهية + التظليل + النانو سيراميك",
             "3,600 – 4,100", "10 سنوات"),
    ],
    "addons_title": "إضافات اختيارية",
    "addons": [
        {"text": "حماية جزئية للواجهة الأمامية فقط (Front Kit)", "icon": ICONS["frontKit"]},
        {"text": "خدمة استلام وتوصيل مجانية داخل نطاق محدد", "icon": ICONS["truck"]},
        {"text": "تقسيط عبر تابي وتمارا وإمكان", "icon": ICONS["card"]},
    ],
    "unsure_title": "غير متأكد من الباقة المناسبة؟",
    "unsure_body": "أرسل لنا نوع سيارتك ونرشّح لك الباقة الأنسب خلال دقائق.",
    "ask_whatsapp": "اسأل على واتساب",

    # ---- Why KMQ ----
    "why_title": "لماذا KMQ",
    "why": [
        {"title": "دقة التركيب", "body": "أغلب عمليات التركيب تتم يدويًا بخبرة فنيين متخصصين لضمان أعلى مستوى دقة، مع توفر خيار القص بالليزر عند الطلب."},
        {"title": "فيلم أمريكي الخامة", "body": "فيلم حماية بمواد خام أمريكية وتصنيع صيني، سماكة 7.5 مللي، بخاصية المعالجة الذاتية للخدوش."},
        {"title": "ضمان حقيقي موثّق", "body": "10 سنوات على الباقة اللامعة، 7 سنوات على المطفية."},
        {"title": "خدمة ما بعد البيع", "body": "أي خدش أو تلف بسيط بعد التركيب يتم إصلاحه على حساب المركز، دون أي تكلفة على العميل."},
        {"title": "تواصل فوري", "body": "رد أول خلال دقائق على واتساب."},
    ],

    # ---- Warranty pitch on the home page ----
    "wb_title": "عشر سنوات مكتوبة، لا وعود شفهية",
    "wb_sub": "ضمان KMQ يغطي جودة التركيب، ثبات اللون، قوة الالتصاق، والمعالجة الذاتية للفيلم — ويُفعَّل من قسم الجودة بعد فحص السيارة، لا تلقائيًا عند الحجز.",
    "wb_years": "10",
    "wb_years_label": "سنوات ضمان",
    "wb_seal": "ضمان موثّق",
    "wb_points": [
        {"title": "جودة التركيب", "body": "التصاق كامل دون فقاعات أو عيوب"},
        {"title": "ثبات اللون", "body": "بدون اصفرار أو تشهيب أو ضبابية"},
        {"title": "إصلاح على حسابنا", "body": "أي خدش بسيط بعد التركيب نتحمله بالكامل"},
    ],
    "wb_cta": "اقرأ تفاصيل الضمان",
    "wb_cta2": "تحقق من ضمانك",

    # ---- Branches ----
    "branches_title": "زورونا في أقرب فرع",
    "branch_page_title": "زورونا في أقرب فرع لك",
    "all_branches_link": "كل الفروع ←",
    "hours_label": "ساعات العمل",
    "branch_wa": "واتساب الفرع",
    "directions": "الاتجاهات",
    "branches": [
        _branch("al-rimal", "فرع حي الرمال", "الرياض", "حي الرمال، الرياض", "الرمال", "RIYADH · MAIN BRANCH"),
        _branch("al-hamra", "فرع حي الحمرا", "الرياض", "حي الحمرا، الرياض", "الحمرا", "RIYADH"),
        _branch("tuwaiq", "فرع حي طويق", "الرياض", "حي طويق، الرياض", "طويق", "RIYADH"),
        _branch("jeddah-madinah-road", "فرع طريق المدينة", "جدة", "طريق المدينة، جدة", "جدة", "JEDDAH"),
        _branch("dammam-al-manar", "فرع حي المنار", "الدمام", "حي المنار، الدمام", "الدمام — المنار", "DAMMAM"),
        _branch("dammam-imam", "فرع حي الإمام محمد بن سعود", "الدمام", "حي الإمام محمد بن سعود، الدمام", "الدمام — الإمام", "DAMMAM"),
    ],
    "map_shot": "[ map: 6 KMQ branches — Riyadh ×3, Jeddah ×1, Dammam ×2 ]",
    "pickup_title": "لا يوجد فرع قريب؟ نوصّل ونستلم سيارتك مجانًا ضمن نطاق محدد",
    "pickup_cta": "اطلب الاستلام على واتساب ←",
    "branch_shot": "مدخل فرع KMQ شيلد — واجهة المعرض وبورشه 911 عند البوابة",
    # Prefixes the branch name and city to build each photograph's alt text.
    "branch_alt": "واجهة",

    # ---- Warranty page ----
    "warranty_page_title": "ضمان KMQ — شفافية كاملة فيما يغطيه الضمان",
    "war_check_title": "تحقق من ضمانك",
    "war_check_sub": "أدخل رقم الفاتورة أو رقم اللوحة لعرض حالة الضمان وتاريخ التفعيل وتاريخ الانتهاء.",
    "war_placeholder": "رقم اللوحة أو رقم الفاتورة",
    "war_check_btn": "تحقق الآن",
    "war_note": "الضمان يُفعَّل من قسم الجودة بعد فحص التركيب، وليس تلقائيًا فور الحجز.",
    "war_found": "الضمان مُفعَّل وساري",
    "war_expired": "انتهت مدة الضمان",
    "war_void": "الضمان غير ساري",
    "war_none": "لم نعثر على ضمان بهذا الرقم",
    "war_none_body": "تأكد من رقم اللوحة أو رقم الفاتورة، أو تواصل معنا على واتساب وسنتحقق لك.",
    "war_empty_query": "أدخل رقم اللوحة أو رقم الفاتورة أولًا.",
    "war_rows": ["رقم الضمان", "الخدمة", "تاريخ التفعيل", "تاريخ الانتهاء"],
    "covered": "البنود التي يشملها الضمان",
    "not_covered_title": "لا يشمل الضمان",
    "conditions_title": "شروط الحفاظ على الضمان",
    "after_sales_title": "خدمة ما بعد البيع",
    "after_sales_body": "إذا تعرض جزء بسيط من السيارة لخدش أو تلف بعد التركيب (مثال: جزء من الرفرف)، تقوم KMQ بنزع الجزء المتضرر من فيلم الحماية، وإعادة تلميع المنطقة، وتركيب فيلم جديد مكانه — على حساب المركز بالكامل، دون أي تكلفة على العميل.",
    "warranty_blocks": [
        {
            "title": "ضمان حماية PPF",
            "years": "10 / 7",
            "years_label": "سنوات — لامع / مطفي وتغيير اللون",
            "covered": [
                "جودة التركيب — التصاق الفيلم دون فقاعات أو عيوب",
                "المتانة — مقاومة التشقق أو التقشر أو أي عيوب سطحية",
                "ثبات اللون دون أي تغيّر",
                "قوة الالتصاق — يبقى الفيلم ملتصقًا دون انفصال",
                "المقاومة — يشمل الاصفرار، التشهيب، الضبابية، أو الاحتراق الناتج عن الحرارة أو أشعة الشمس",
                "حماية بوية الوكالة الأصلية في حال فك الفيلم",
                "معالجة الفيلم ذاتيًا طوال فترة الضمان",
            ],
        },
        {
            "title": "ضمان النانو سيراميك",
            "years": "2",
            "years_label": "سنتان، مع طبقة نانو سيراميك مجانية كل سنة",
            "covered": [
                "ثبات اللمعان وحماية الطلاء من الخدوش البسيطة",
                "مقاومة العوامل البيئية كالأتربة وأشعة الشمس",
                "سهولة تنظيف سطح السيارة والحفاظ على النعومة واللمعان",
                "طبقة نانو سيراميك إضافية مجانية كل سنة",
            ],
        },
        {
            "title": "ضمان التظليل العازل الحراري",
            "years": "10",
            "years_label": "سنوات",
            "covered": [
                "ثبات لون الفيلم وعدم تغيّره مع الوقت",
                "الحفاظ على كفاءة العزل الحراري",
                "مقاومة تكوّن فقاعات الهواء أو انفصال الفيلم عن الزجاج",
                "الاستبدال المجاني في حال حدوث أي خلل مشمول بالضمان",
            ],
        },
    ],
    "not_covered": [
        "أضرار سوء الاستخدام أو الحوادث",
        "التعديل أو الإصلاح من جهة غير معتمدة من KMQ",
        "عدم اتباع تعليمات العناية الموصى بها",
    ],
    "conditions": [
        "الالتزام بتعليمات العناية الموصى بها",
        "تجنب تنظيف الفيلم بمواد كيميائية قوية أو أدوات خشنة",
        "عدم وضع ملصقات أو أشرطة لاصقة على الفيلم",
        "يُوصى بزيارة الفرع خلال 72 ساعة بعد التركيب للتأكد من جودة التركيب",
        "التركيب والإصلاح يجب أن يتم في فروع KMQ المعتمدة فقط",
    ],
    "no_maintenance_note": "في حال حدوث أي خلل مشمول بالضمان، يتم الفحص الفوري والمعالجة أو الاستبدال مجانًا دون الحاجة لصيانة دورية.",

    # ---- Film spec ----
    "spec_title": "مواصفات الفيلم المستخدم",
    "spec_sub": "فيلم حماية بمواد خام أمريكية وتصنيع صيني، سماكة 7.5 مللي، بخاصية المعالجة الذاتية للخدوش.",
    "film_spec": [
        {"k": "نوع الفيلم", "v": "خامة أمريكية، تصنيع صيني"},
        {"k": "السماكة", "v": "7.5 مللي"},
        {"k": "الخامة", "v": "TPU مع معالجة ذاتية للخدوش البسيطة"},
        {"k": "نسبة المعالجة الذاتية", "v": "أكثر من 85%"},
        {"k": "الضمان — باقة لامع", "v": "10 سنوات"},
        {"k": "الضمان — باقة مطفي", "v": "7 سنوات"},
        {"k": "طريقة القص", "v": "يدوي بخبرة فنيين متخصصين في أغلب الحالات، مع توفر خيار القص بالليزر حسب الطلب"},
    ],
    "other_services_title": "خدمات أخرى",

    # ---- About ----
    "about_title": "KMQ — بيت حماية احترافي للسيارات الفاخرة والمتوسطة العليا",
    "about_lead": "KMQ علامة سعودية متخصصة في حماية وتجميل السيارات، تقدم خدمات حماية الطلاء (PPF)، النانو سيراميك، التظليل العازل الحراري، وتغيير اللون. نعمل في السوق السعودي منذ أكثر من 3 سنوات ونصف، بثلاثة فروع في الرياض (حي الرمال، حي الحمرا، حي طويق)، فرع في جدة (طريق المدينة)، وفرعين في الدمام (حي المنار، حي الإمام محمد بن سعود)، ونخدم مالكي السيارات الفاخرة والمتوسطة العليا الذين يبحثون عن حماية حقيقية، تسعير واضح، وتجربة تستحق وقتهم.",
    "about_lead2": "نؤمن أن حماية سيارتك قرار يستحق الشفافية الكاملة، وأن التجربة داخل الفرع يجب أن تكون بمستوى فخامة السيارات التي نعتني بها.",
    "about_values": "قيمنا",
    "about_value_list": [
        {"title": "الشفافية", "body": "تسعير ثابت في 3 باقات، بدون تفاوض مطوّل."},
        {"title": "الدقة الفنية", "body": "تركيب يدوي دقيق بخبرة فنيين متخصصين، مع خيار القص بالليزر عند الطلب."},
        {"title": "الضمان الحقيقي", "body": "10 سنوات على اللامع، 7 سنوات على المطفي."},
    ],
    "about_numbers": "KMQ بالأرقام",
    "about_stats": [
        {"value": "6", "label": "فروع في الرياض وجدة والدمام"},
        {"value": "3", "label": "مدن رئيسية"},
        {"value": "10", "label": "سنوات ضمان على الباقة اللامعة"},
        {"value": "7.5", "label": "مللي سماكة الفيلم المستخدم"},
    ],
    "about_cta": "تعرف علينا من قرب — زر أقرب فرع",
    "about_shot": "صالة عرض KMQ شيلد — بورشه 911 GT3 زرقاء بعد تركيب فيلم الحماية",

    # ---- FAQ. Section 10 of the document; the design file had no FAQ. ----
    "faq_title": "الأسئلة الشائعة",
    "faq": [
        {"q": "هل النانو سيراميك بنفس حماية الـ PPF؟",
         "a": "لا، النانو سيراميك بديل تجميلي واقتصادي يحسّن اللمعان ويقاوم الأتربة، لكنه لا يوفر نفس مستوى الحماية الهيكلية ضد الخدوش والحصى مثل فيلم PPF السميك."},
        {"q": "ما الفرق بين الحماية اللامعة والمطفية؟",
         "a": "اللامعة أفضل في مقاومة الخدوش اليومية مع معالجة ذاتية، بينما المطفية تركيبها أدق فنيًا وتمنح مظهرًا مختلفًا عن طلاء الوكالة الأصلي."},
        {"q": "كم مدة الضمان وماذا يشمل؟",
         "a": "10 سنوات على باقة الحماية اللامعة، 7 سنوات على باقة الحماية المطفية وباقة تغيير اللون. التفاصيل الكاملة في صفحة الضمان."},
        {"q": "ما نوع الفيلم المستخدم في الحماية؟",
         "a": "فيلم حماية عالي الجودة، بمواد خام أمريكية وتصنيع صيني."},
        {"q": "هل التركيب يدوي أم بالليزر؟",
         "a": "الغالبية العظمى من التركيبات تتم يدويًا بخبرة فنيينا المتخصصين، مع توفر خيار القص بالليزر عند الطلب."},
        {"q": "هل يوجد خدمة استلام وتوصيل؟",
         "a": "نعم، ضمن نطاق جغرافي محدد حول فروعنا."},
        {"q": "هل يمكن التقسيط؟",
         "a": "نعم، عبر تابي وتمارا وإمكان."},
        {"q": "كم تستغرق عملية التركيب؟",
         "a": "تختلف حسب نوع الخدمة والباقة المختارة."},
        {"q": "ماذا لو حصل خدش بسيط في السيارة بعد التركيب؟",
         "a": "يتم نزع الجزء المتضرر من الفيلم، وإعادة تلميع المنطقة، وتركيب فيلم جديد مكانه — على حساب المركز بالكامل، دون أي تكلفة عليك."},
    ],

    # ---- Blog ----
    "blog_title": "من المدونة",
    "blog_page_title": "مدونة KMQ — دلائل ومقارنات قبل ما تحمي سيارتك",
    "blog_page_sub": "مقالات تشرح الفرق بين أنواع الحماية، الأسعار الواقعية في السعودية، وطريقة العناية بسيارتك بعد التركيب.",
    "all_blog_link": "كل المقالات ←",
    "featured": "مقال مميز",
    "search_placeholder": "ابحث في المدونة",
    "all_cats": "كل المقالات",
    "categories": [
        {"slug": "guides", "label": "دلائل"},
        {"slug": "comparisons", "label": "مقارنات"},
        {"slug": "pricing", "label": "أسعار"},
        {"slug": "care", "label": "العناية"},
        {"slug": "tinting", "label": "تظليل"},
    ],
    "results_one": "مقال واحد",
    "results_many": " مقالات",
    "no_results": "لا توجد مقالات مطابقة لبحثك. جرّب كلمة أخرى أو تصنيفًا مختلفًا.",
    "popular": "الأكثر قراءة",
    "by_category": "التصنيفات",
    "tags_title": "الوسوم",
    "tags": ["PPF", "نانو سيراميك", "تظليل", "تغيير اللون", "ضمان", "الرياض", "جدة", "العناية"],
    "news_title": "وصلك كل مقال جديد",
    "news_body": "اشترك واستلم دليلًا واحدًا شهريًا عن حماية السيارات — بدون إزعاج.",
    "news_placeholder": "بريدك الإلكتروني",
    "news_cta": "اشترك",
    "blog_aside_cta": "عندك سؤال عن سيارتك تحديدًا؟ فريقنا يجاوبك مباشرة",
    "prev": "السابق",
    "next": "التالي",
    "min_read": " دقائق قراءة",
    "article_shot": "[ article thumbnail ]",
    "article_cta": "احجز فحص مجاني على واتساب",
    "article_pending": "هذا المقال قيد التحرير. العنوان والملخص معتمدان من ملف المحتوى؛ النص الكامل يصل مع الدفعة التحريرية القادمة.",
    "back_to_blog": "← كل المقالات",
    # Titles are the document's section 8 list, in its order. Excerpts and
    # dates are editorial scaffolding: the document supplies titles only.
    "posts": [
        _post("ppf-vs-nano-ceramic", "الفرق بين حماية PPF والنانو سيراميك — أيهما يناسبك؟",
              "مقارنة عملية بين الحماية الهيكلية والحل التجميلي، ومتى يكون كل خيار هو الأنسب لسيارتك وميزانيتك.",
              "comparisons", "14 مارس 2026", 8, "فريق KMQ"),
        _post("gloss-or-matte", "حماية لامع أم مطفي؟ دليلك الكامل قبل القرار",
              "اللمعان يبرز لون الوكالة، والمطفي يعطي مظهرًا فريدًا — لكن الفرق يمتد إلى الضمان والعناية اليومية.",
              "comparisons", "2 مارس 2026", 6, "فريق KMQ"),
        _post("ppf-price-guide-2026", "كم تكلفة حماية PPF في الرياض وجدة؟ (دليل أسعار 2026)",
              "أرقام واقعية لكل باقة، وما الذي يجعل السعر يرتفع أو ينخفض من سيارة لأخرى.",
              "pricing", "21 فبراير 2026", 7, "قسم الجودة"),
        _post("what-is-self-healing", "ما هي المعالجة الذاتية للخدوش (Self Healing) ولماذا هي مهمة؟",
              "كيف يعيد الفيلم ترميم الخدوش السطحية بنفسه، وما الذي يحدد نسبة المعالجة.",
              "guides", "9 فبراير 2026", 5, "فريق التركيب"),
        _post("hand-cut-vs-laser", "التركيب اليدوي والقص بالليزر — إيه الفرق ومتى يُستخدم كل منهما؟",
              "لماذا نبدأ يدويًا في أغلب الحالات، ومتى يكون القص بالليزر هو الخيار الأنسب.",
              "guides", "28 يناير 2026", 6, "فريق التركيب"),
        _post("colour-change-resale", "هل تغيير لون السيارة يؤثر على الضمان أو قيمة إعادة البيع؟",
              "ما الذي يحدث لطلاء الوكالة تحت الفيلم الملوّن، وكيف ينعكس ذلك على القيمة عند البيع.",
              "guides", "15 يناير 2026", 9, "قسم الجودة"),
        _post("care-after-ppf", "دليل العناية بسيارتك بعد تركيب حماية PPF",
              "الفترة الأولى هي الأهم لثبات الفيلم. خطوات بسيطة تحافظ على النتيجة وعلى ضمانك.",
              "care", "4 يناير 2026", 4, "فريق KMQ"),
        _post("tint-faq-saudi", "أسئلة شائعة عن التظليل العازل الحراري في السعودية",
              "نسب العزل، الأنظمة المسموحة، وكيف تختار الدرجة المناسبة لصيف السعودية.",
              "tinting", "22 ديسمبر 2025", 6, "فريق KMQ"),
    ],

    # ---- Contact ----
    "contact_title": "تواصل معنا — نرد خلال دقائق",
    "contact_sub": "أرسل لنا تفاصيل سيارتك وسنرشّح لك الأنسب. أو ابدأ محادثة واتساب مباشرة.",
    "contact_form_title": "أرسل طلبك",
    "contact_form_sub": "املأ الحقول التالية وسنرشّح لك الأنسب لسيارتك.",
    "contact_form_note": "الحقول المعلّمة بـ * مطلوبة. نرد على الطلبات خلال ساعات العمل.",
    "contact_submit": "أرسل الطلب",
    "contact_ok_title": "وصلنا طلبك",
    "contact_ok_body": "شكرًا لك. سيتواصل معك أحد المختصين خلال ساعات العمل.",
    "contact_bad": "لم نتمكن من إرسال الطلب. راجع الحقول المعلّمة بالأسفل.",
    "contact_phones_title": "أرقام الفروع",
    "required_mark": "مطلوب",
    "optional_mark": "اختياري",
    "choose": "اختر…",

    # ---- Footer ----
    "footer_blurb": "كي إم كيو لخدمات حماية وتظليل السيارات — الرياض، جدة، الدمام.",
    "footer_nav": "الموقع",
    "footer_phones": "أرقام الفروع",
    "footer_hours": "ساعات العمل",
    "hours_week": "السبت — الخميس: 10:00 ص — 11:00 م",
    "hours_fri": "الجمعة: 4:00 م — 11:00 م",
    "installments": "تقسيط عبر تابي وتمارا وإمكان",
    # `icon` names a glyph in partials/icons.html, all four of them from the
    # client's own kit. Facebook joins the list because the kit ships that
    # glyph too; like the other three, its URL is still pending.
    "social": [
        {"name": "إنستجرام", "icon": "instagram", "url": TBD},
        {"name": "تيك توك", "icon": "tiktok", "url": TBD},
        {"name": "سناب شات", "icon": "snapchat", "url": TBD},
        {"name": "فيسبوك", "icon": "facebook", "url": TBD},
    ],
    "skip_link": "تخطَّ إلى المحتوى",
    "menu_label": "القائمة",
    "final_title": "احجز فحص مجاني لسيارتك الآن",
    "final_sub": "واعرف السعر النهائي خلال دقائق على واتساب — بدون التزام",
    "not_found_title": "الصفحة غير موجودة",
    "not_found_body": "الرابط الذي طلبته غير متاح. جرّب الرئيسية أو تواصل معنا.",
    "error_title": "حدث خطأ",
    "error_body": "تعذّر عرض الصفحة. حاول مرة أخرى، أو تواصل معنا على واتساب.",
}


# ==========================================================================
# English. Data tables come from the document's Part Two; prose that the
# document supplies in Arabic only is translated from it.
# ==========================================================================

EN: dict[str, Any] = {
    "lang": "en",
    "dir": "ltr",
    "other_lang": "ar",
    "other_label": "ع",
    "locale_name": "English",

    "brand_tagline": "KMQ car protection and window tinting services",
    "tbd": "To be confirmed",

    "cta_book": "Book a Free Inspection",
    "cta_whatsapp": "Message us on WhatsApp",
    "cta_contact": "Contact us",
    "learn_more": "Learn more →",

    "nav": [
        {"key": "home", "label": "Home"},
        {"key": "about", "label": "About"},
        {"key": "services", "label": "Services"},
        {"key": "packages", "label": "Packages"},
        {"key": "warranty", "label": "Warranty"},
        {"key": "branches", "label": "Branches"},
        {"key": "blog", "label": "Journal"},
        {"key": "contact", "label": "Contact"},
    ],

    "wa_default": "Hello, I would like to know more about KMQ services",
    "wa_order": "Hello, I would like to order ",
    "wa_book": "Hello, I would like to book at ",
    "wa_contact": "Hello KMQ, I have a question about protecting my car and would like to speak to a specialist",
    "phone_primary": PHONE_PRIMARY,
    "phone_primary_e164": PHONE_PRIMARY_E164,
    "call_us": "Call us",
    "wa_pickup": "Hello, I would like to request the pickup and delivery service",

    "hero_kicker": "PPF · CERAMIC · TINT · WRAP",
    "hero_a": "A professional protection house",
    "hero_b": "for your luxury car",
    "hero_sub": "Clear pricing from the first message, and precise installation by specialist technicians — in Riyadh, Jeddah and Dammam",
    "hero_cta1": "Book a free inspection on WhatsApp",
    "hero_cta2": "See our packages",
    "hero_shot": "[ hero image: PPF film being applied — dramatic side light, black Porsche ]",

    "stack_kicker": "00 — PROTECTION STACK",
    "stack": [
        {"code": "01 BARE PAINT",   "a": "Your car as it",      "b": "left the factory",
         "body": "The original paint, with nothing protecting it. Scroll down to see the three layers we add."},
        {"code": "02 PPF FILM",     "a": "Paint protection",    "b": "film PPF",
         "body": "A clear self-healing layer that takes the scratches and the road stones before they reach the paint."},
        {"code": "03 THERMAL TINT", "a": "Thermal",             "b": "tint",
         "body": "Blocks ultraviolet light and brings the cabin temperature down, at a specification that meets the Saudi regulation."},
        {"code": "04 CERAMIC COAT", "a": "Ceramic",             "b": "coating",
         "body": "A glass-like gloss that repels water and dust, so washing is quicker and the car stays clean for longer."},
    ],
    "stack_shot": "Three-quarter front view of an SUV",

    "trust": [
        {"title": "Warranty up to 10 years", "meta": "UP TO 10 YEARS", "icon": ICONS["shield"]},
        {"title": "Precise hand-cut installation", "meta": "HAND-CUT PRECISION", "icon": ICONS["blade"]},
        {"title": "6 branches — Riyadh, Jeddah, Dammam", "meta": "3 CITIES · 6 BRANCHES", "icon": ICONS["pin"]},
        {"title": "Instant reply on WhatsApp", "meta": "REPLY IN MINUTES", "icon": ICONS["chat"]},
    ],

    "services_title": "Complete protection and finishing services for your car",
    "services_page_title": "Our services — protection and finishing, on stated terms",
    "services_page_sub": "Five services, each with published specifications and a published warranty. Choose what fits your car and your budget.",
    "services": [
        _svc(
            "ppf-gloss", "Gloss PPF", "Real structural protection for your paint against scratches and stone chips.",
            ICONS["shieldLine"],
            "A 7.5 mil clear protection film that shields your paint from daily scratches and stone chips, with a gloss that brings out the original factory colour.",
            [
                "High resistance to daily scratches",
                "Self-healing for light scratches",
                "10-year warranty — full details on the warranty page",
                "Precise hand installation, with laser cutting on request",
            ],
            "10 years",
            "A technician squeegeeing clear protection film onto the bonnet of a grey saloon",
        ),
        _svc(
            "ppf-matte", "Matte PPF", "A distinctive finish, installed to the same precision.",
            ICONS["shieldLine"],
            "A protection film with a non-gloss finish that gives the car a look distinct from the original factory paint, with the same level of structural protection.",
            [
                "A distinctive look that sets your car apart",
                "Heat resistant",
                "7-year warranty — full details on the warranty page",
                "Precise hand installation, with laser cutting on request",
            ],
            "7 years",
            "A technician in KMQ uniform working the edge of matte protection film on a matte black Porsche",
        ),
        _svc(
            "nano-ceramic", "Nano ceramic", "Exceptional gloss, as the economical alternative.",
            ICONS["droplet"],
            "Nano ceramic is a cheaper alternative to PPF, but not at the same level of protection. It is a thin chemical layer that improves gloss and resists dust and water, but it does not stop scratches or stone chips the way thick PPF film does.",
            [
                "Over 75% gloss (as an added layer over PPF, or on its own)",
                "Dust and water resistant (hydrophobic)",
                "An economical option for a smaller budget",
                "A cosmetic solution — not a full structural replacement for PPF",
            ],
            "2 years",
            "A gloved hand spreading nano ceramic with a microfibre cloth over a gloss black bonnet, water beading on the surface",
        ),
        _svc(
            "window-tint", "Heat-insulating tint", "A cooler cabin from the first day.",
            ICONS["sun"],
            "Heat-insulating film that reduces the heat and radiation entering the car.",
            [
                "Lower cabin temperature",
                "Protection from ultraviolet rays",
                "Several tint grades within the permitted regulations",
                "A competitive entry price",
            ],
            "10 years",
            "A driver sitting comfortably inside a blue car under harsh sun, heat reflecting off the glass while the cabin air stays cool",
        ),
        _svc(
            "colour-change", "Colour change", "Redefine how your car looks, completely.",
            ICONS["roller"],
            "A full exterior colour change in any colour you choose, professionally installed, with a warranty of up to 7 years.",
            [
                "A free choice of dozens of colours and finishes",
                "Approximate turnaround: 10 to 15 days",
                "7-year warranty",
                "Can be combined with coloured PPF protection",
            ],
            "7 years",
            "A gloved hand holding a fan of colour swatches in front of a dark car",
        ),
    ],

    "packages_title": "Clear packages, fixed prices, no haggling",
    "packages_page_title": "Clear packages, fixed prices — choose what fits your car",
    "most_chosen": "Most chosen",
    "sar": "Saudi Riyal",
    "warranty_label": "Warranty",
    "order_package": "Order this package",
    "order_on_whatsapp": "Order this package on WhatsApp",
    "all_packages_link": "All package details and add-ons →",
    "packages": [
        _pkg("gloss", "Gloss Protection Package",
             "Full-body gloss PPF + nano ceramic + free add-ons",
             "6,000 – 7,500", "10 years"),
        _pkg("matte", "Matte Protection Package",
             "Full-body matte PPF + nano ceramic + free add-ons",
             "7,000 – 8,000", "7 years"),
        _pkg("colour-change", "Colour Change Package",
             "Full-body colour-change PPF film, in any colour you choose",
             "8,500 – 12,500", "7 years"),
        _pkg("nano-ceramic", "Nano Ceramic Package",
             "Full-body nano ceramic coating",
             "1,100 – 1,650", "Varies by layer type"),
        _pkg("window-tint", "Heat Insulation Package",
             "Full-vehicle heat-insulating tint",
             "700 – 900", "10 years"),
        _pkg("front-kit", "Front End Package",
             "Front-end PPF",
             "2,200 – 2,700", "10 years"),
        _pkg("quarter-front", "Quarter Front Package",
             "Quarter front-end PPF",
             "1,100 – 1,450", "10 years"),
        _pkg("combo", "Combo Package",
             "Front-end PPF + heat-insulating tint + nano ceramic",
             "3,600 – 4,100", "10 years"),
    ],
    "addons_title": "Optional add-ons",
    "addons": [
        {"text": "Partial front-end protection only (Front Kit)", "icon": ICONS["frontKit"]},
        {"text": "Free pickup and delivery within a set radius", "icon": ICONS["truck"]},
        {"text": "Instalments via Tabby, Tamara and Emkan", "icon": ICONS["card"]},
    ],
    "unsure_title": "Not sure which package fits?",
    "unsure_body": "Send us your car model and we will recommend the right package within minutes.",
    "ask_whatsapp": "Ask on WhatsApp",

    "why_title": "Why KMQ",
    "why": [
        {"title": "Installation precision", "body": "Most installation work is done by hand by specialist technicians for the highest level of precision, with laser cutting available on request."},
        {"title": "American-made film", "body": "Protection film made from American raw materials with Chinese manufacturing, 7.5 mil thick, with self-healing for scratches."},
        {"title": "A real, documented warranty", "body": "10 years on the gloss package, 7 years on the matte package."},
        {"title": "After-sales service", "body": "Any minor scratch or damage after installation is repaired at the centre's expense, at no cost to the customer."},
        {"title": "Instant contact", "body": "First reply within minutes on WhatsApp."},
    ],

    "wb_title": "Ten years in writing, not a verbal promise",
    "wb_sub": "The KMQ warranty covers installation quality, colour stability, adhesion strength and the film's self-healing — and it is activated by the quality department after inspecting the car, not automatically on booking.",
    "wb_years": "10",
    "wb_years_label": "year warranty",
    "wb_seal": "Documented warranty",
    "wb_points": [
        {"title": "Installation quality", "body": "Full adhesion with no bubbles or defects"},
        {"title": "Colour stability", "body": "No yellowing, staining or hazing"},
        {"title": "Repairs at our expense", "body": "Any minor scratch after installation is fully on us"},
    ],
    "wb_cta": "Read the warranty details",
    "wb_cta2": "Check your warranty",

    "branches_title": "Visit your nearest branch",
    "branch_page_title": "Visit your nearest branch",
    "all_branches_link": "All branches →",
    "hours_label": "Working hours",
    "branch_wa": "Branch WhatsApp",
    "directions": "Directions",
    "branches": [
        _branch("al-rimal", "Al Rimal Branch", "Riyadh", "Al Rimal district, Riyadh", "Al Rimal", "RIYADH · MAIN BRANCH"),
        _branch("al-hamra", "Al Hamra Branch", "Riyadh", "Al Hamra district, Riyadh", "Al Hamra", "RIYADH"),
        _branch("tuwaiq", "Tuwaiq Branch", "Riyadh", "Tuwaiq district, Riyadh", "Tuwaiq", "RIYADH"),
        _branch("jeddah-madinah-road", "Al Madinah Road Branch", "Jeddah", "Al Madinah Road, Jeddah", "Jeddah", "JEDDAH"),
        _branch("dammam-al-manar", "Al-Manar Branch", "Dammam", "Al-Manar district, Dammam", "Dammam — Al-Manar", "DAMMAM"),
        _branch("dammam-imam", "Al-Imam Muhammad bin Saud Branch", "Dammam", "Al-Imam Muhammad bin Saud district, Dammam", "Dammam — Al-Imam", "DAMMAM"),
    ],
    "map_shot": "[ map: 6 KMQ branches — Riyadh ×3, Jeddah ×1, Dammam ×2 ]",
    "pickup_title": "No branch nearby? We collect and deliver your car free within a set radius",
    "pickup_cta": "Request pickup on WhatsApp →",
    "branch_shot": "The entrance to a KMQ Shield branch — the showroom facade with a Porsche 911 at the door",
    "branch_alt": "The storefront of",

    "warranty_page_title": "The KMQ warranty — full transparency on what is covered",
    "war_check_title": "Check your warranty",
    "war_check_sub": "Enter your invoice number or plate number to view warranty status, activation date and expiry date.",
    "war_placeholder": "Plate number or invoice number",
    "war_check_btn": "Check now",
    "war_note": "The warranty is activated by the quality department after the installation inspection, not automatically on booking.",
    "war_found": "Warranty active and valid",
    "war_expired": "This warranty has expired",
    "war_void": "This warranty is not valid",
    "war_none": "We could not find a warranty with that number",
    "war_none_body": "Check the plate or invoice number, or message us on WhatsApp and we will look it up for you.",
    "war_empty_query": "Enter a plate number or invoice number first.",
    "war_rows": ["Warranty number", "Service", "Activation date", "Expiry date"],
    "covered": "What the warranty covers",
    "not_covered_title": "Not covered",
    "conditions_title": "Conditions for keeping the warranty valid",
    "after_sales_title": "After-sales service",
    "after_sales_body": "If a small part of the car is scratched or damaged after installation (for example part of a fender), KMQ removes the damaged section of protection film, re-polishes the area and installs new film in its place — entirely at the centre's expense, at no cost to the customer.",
    "warranty_blocks": [
        {
            "title": "PPF warranty",
            "years": "10 / 7",
            "years_label": "years — gloss / matte and colour change",
            "covered": [
                "Installation quality — film adhesion with no bubbles or defects",
                "Durability — resistance to cracking, peeling or any surface defects",
                "Colour stability with no change over time",
                "Adhesion strength — the film stays bonded without lifting",
                "Resistance — covers yellowing, staining, hazing or burn caused by heat or sunlight",
                "Protection of the original factory paint when the film is removed",
                "Self-healing of the film throughout the warranty period",
            ],
        },
        {
            "title": "Nano ceramic warranty",
            "years": "2",
            "years_label": "years, with a free nano ceramic layer every year",
            "covered": [
                "Gloss retention and protection of the paint from light scratches",
                "Resistance to environmental factors such as dust and sunlight",
                "Easy cleaning while keeping the surface smooth and glossy",
                "One additional free nano ceramic layer every year",
            ],
        },
        {
            "title": "Heat-insulating tint warranty",
            "years": "10",
            "years_label": "years",
            "covered": [
                "Film colour stays stable and does not change over time",
                "Heat insulation performance is maintained",
                "Resistance to air bubbles or the film separating from the glass",
                "Free replacement if any covered defect occurs",
            ],
        },
    ],
    "not_covered": [
        "Damage from misuse or accidents",
        "Modification or repair by a party not approved by KMQ",
        "Failure to follow the recommended care instructions",
    ],
    "conditions": [
        "Follow the recommended care instructions",
        "Avoid cleaning the film with harsh chemicals or abrasive tools",
        "Do not apply stickers or adhesive tape to the film",
        "A branch visit within 72 hours of installation is recommended to confirm installation quality",
        "Installation and repair must be carried out at approved KMQ branches only",
    ],
    "no_maintenance_note": "If any covered defect occurs, KMQ provides immediate inspection and free repair or replacement, with no periodic maintenance required to keep the warranty valid.",

    "spec_title": "Specifications of the film we use",
    "spec_sub": "Protection film made from American raw materials with Chinese manufacturing, 7.5 mil thick, with self-healing for light scratches.",
    "film_spec": [
        {"k": "Film origin", "v": "American raw material, manufactured in China"},
        {"k": "Thickness", "v": "7.5 mil"},
        {"k": "Material", "v": "TPU with a self-healing top coat"},
        {"k": "Self-healing rate", "v": "85%+"},
        {"k": "Warranty — gloss package", "v": "10 years"},
        {"k": "Warranty — matte package", "v": "7 years"},
        {"k": "Cutting method", "v": "Primarily hand-cut by trained technicians, laser cutting available on request"},
    ],
    "other_services_title": "Other services",

    "about_title": "KMQ — a professional protection house for luxury and upper-mid cars",
    "about_lead": "KMQ is a Saudi brand specialising in car protection and finishing, offering paint protection film (PPF), nano ceramic, heat-insulating tint and colour change. We have worked in the Saudi market for more than three and a half years, with three branches in Riyadh (Al Rimal, Al Hamra and Tuwaiq), one in Jeddah (Al Madinah Road) and two in Dammam (Al-Manar and Al-Imam Muhammad bin Saud), serving owners of luxury and upper-mid cars who are looking for real protection, clear pricing, and an experience worth their time.",
    "about_lead2": "We believe protecting your car is a decision that deserves complete transparency, and that the experience inside the branch should match the quality of the cars we look after.",
    "about_values": "Our values",
    "about_value_list": [
        {"title": "Transparency", "body": "Fixed pricing across 3 packages, without drawn-out haggling."},
        {"title": "Technical precision", "body": "Precise hand installation by specialist technicians, with laser cutting available on request."},
        {"title": "A real warranty", "body": "10 years on gloss, 7 years on matte."},
    ],
    "about_numbers": "KMQ in numbers",
    "about_stats": [
        {"value": "6", "label": "branches in Riyadh, Jeddah and Dammam"},
        {"value": "3", "label": "major cities"},
        {"value": "10", "label": "year warranty on the gloss package"},
        {"value": "7.5", "label": "mil thickness of the film we use"},
    ],
    "about_cta": "Get to know us in person — visit your nearest branch",
    "about_shot": "The KMQ Shield showroom — a blue Porsche 911 GT3 after paint protection film",

    "faq_title": "Frequently asked questions",
    "faq": [
        {"q": "Does nano ceramic protect as well as PPF?",
         "a": "No. Nano ceramic is a cosmetic, economical alternative that improves gloss and resists dust, but it does not provide the same level of structural protection against scratches and stone chips as thick PPF film."},
        {"q": "What is the difference between gloss and matte protection?",
         "a": "Gloss is better at resisting daily scratches and self-heals, while matte is more technically demanding to install and gives a look distinct from the original factory paint."},
        {"q": "How long is the warranty and what does it cover?",
         "a": "10 years on the gloss protection package, 7 years on the matte protection package and the colour change package. Full details are on the warranty page."},
        {"q": "What type of film do you use?",
         "a": "A high-quality protection film, made from American raw materials with Chinese manufacturing."},
        {"q": "Is installation done by hand or by laser?",
         "a": "The great majority of installations are done by hand by our specialist technicians, with laser cutting available on request."},
        {"q": "Do you offer pickup and delivery?",
         "a": "Yes, within a defined geographic radius around our branches."},
        {"q": "Can I pay in instalments?",
         "a": "Yes, via Tabby, Tamara and Emkan."},
        {"q": "How long does installation take?",
         "a": "It varies by the service and the package you choose."},
        {"q": "What if my car gets a minor scratch after installation?",
         "a": "We remove the damaged section of film, re-polish the area and install new film in its place — entirely at the centre's expense, at no cost to you."},
    ],

    "blog_title": "From the journal",
    "blog_page_title": "The KMQ journal — guides and comparisons before you protect your car",
    "blog_page_sub": "Articles explaining the differences between protection types, realistic prices in Saudi Arabia, and how to care for your car after installation.",
    "all_blog_link": "All articles →",
    "featured": "Featured",
    "search_placeholder": "Search the journal",
    "all_cats": "All articles",
    "categories": [
        {"slug": "guides", "label": "Guides"},
        {"slug": "comparisons", "label": "Comparisons"},
        {"slug": "pricing", "label": "Pricing"},
        {"slug": "care", "label": "Care"},
        {"slug": "tinting", "label": "Tinting"},
    ],
    "results_one": "1 article",
    "results_many": " articles",
    "no_results": "No articles match your search. Try another keyword or a different category.",
    "popular": "Most read",
    "by_category": "Categories",
    "tags_title": "Tags",
    "tags": ["PPF", "Nano ceramic", "Tinting", "Colour change", "Warranty", "Riyadh", "Jeddah", "Care"],
    "news_title": "Get every new article",
    "news_body": "Subscribe and receive one guide a month on car protection — no spam.",
    "news_placeholder": "Your email address",
    "news_cta": "Subscribe",
    "blog_aside_cta": "Have a question about your specific car? Our team answers directly",
    "prev": "Previous",
    "next": "Next",
    "min_read": " min read",
    "article_shot": "[ article thumbnail ]",
    "article_cta": "Book a free inspection on WhatsApp",
    "article_pending": "This article is being written. The title and summary are approved in the content file; the full text arrives with the next editorial batch.",
    "back_to_blog": "← All articles",
    "posts": [
        _post("ppf-vs-nano-ceramic", "PPF vs nano ceramic — which one is right for you?",
              "A practical comparison between structural protection and the cosmetic option, and when each one suits your car and budget.",
              "comparisons", "14 March 2026", 8, "KMQ Team"),
        _post("gloss-or-matte", "Gloss or matte? Your complete guide before deciding",
              "Gloss brings out the factory colour and matte gives a distinctive look — but the difference extends to warranty and daily care.",
              "comparisons", "2 March 2026", 6, "KMQ Team"),
        _post("ppf-price-guide-2026", "What does PPF cost in Riyadh and Jeddah? (2026 price guide)",
              "Realistic figures for every package, and what makes the price rise or fall from one car to another.",
              "pricing", "21 February 2026", 7, "Quality Department"),
        _post("what-is-self-healing", "What is self-healing, and why does it matter?",
              "How the film repairs light surface scratches on its own, and what determines the healing rate.",
              "guides", "9 February 2026", 5, "Installation Team"),
        _post("hand-cut-vs-laser", "Hand-cut vs laser cutting — what is the difference, and when is each used?",
              "Why we start by hand in most cases, and when laser cutting is the better choice.",
              "guides", "28 January 2026", 6, "Installation Team"),
        _post("colour-change-resale", "Does changing your car's colour affect the warranty or resale value?",
              "What happens to the factory paint under coloured film, and how that shows up at resale.",
              "guides", "15 January 2026", 9, "Quality Department"),
        _post("care-after-ppf", "How to care for your car after PPF installation",
              "The first period matters most for film adhesion. Simple steps that protect the result and your warranty.",
              "care", "4 January 2026", 4, "KMQ Team"),
        _post("tint-faq-saudi", "Common questions about heat-insulating tint in Saudi Arabia",
              "Rejection ratings, the permitted regulations, and how to choose the right grade for a Saudi summer.",
              "tinting", "22 December 2025", 6, "KMQ Team"),
    ],

    "contact_title": "Contact us — we reply within minutes",
    "contact_sub": "Send us your car details and we will recommend what fits. Or start a WhatsApp conversation directly.",
    "contact_form_title": "Send your request",
    "contact_form_sub": "Fill in the fields below and we will recommend what fits your car.",
    "contact_form_note": "Fields marked * are required. We reply to requests during working hours.",
    "contact_submit": "Send request",
    "contact_ok_title": "We have your request",
    "contact_ok_body": "Thank you. A specialist will be in touch during working hours.",
    "contact_bad": "We could not send your request. Check the fields marked below.",
    "contact_phones_title": "Branch phone numbers",
    "required_mark": "required",
    "optional_mark": "optional",
    "choose": "Choose…",

    "footer_blurb": "KMQ car protection and window tinting services — Riyadh, Jeddah, Dammam.",
    "footer_nav": "Site",
    "footer_phones": "Branch phones",
    "footer_hours": "Working hours",
    "hours_week": "Saturday — Thursday: 10:00 AM — 11:00 PM",
    "hours_fri": "Friday: 4:00 PM — 11:00 PM",
    "installments": "Instalments via Tabby, Tamara and Emkan",
    "social": [
        {"name": "Instagram", "icon": "instagram", "url": TBD},
        {"name": "TikTok", "icon": "tiktok", "url": TBD},
        {"name": "Snapchat", "icon": "snapchat", "url": TBD},
        {"name": "Facebook", "icon": "facebook", "url": TBD},
    ],
    "skip_link": "Skip to content",
    "menu_label": "Menu",
    "final_title": "Book a free inspection for your car now",
    "final_sub": "Get your final price within minutes on WhatsApp — no obligation",
    "not_found_title": "Page not found",
    "not_found_body": "That link is not available. Try the home page, or get in touch.",
    "error_title": "Something went wrong",
    "error_body": "We could not render that page. Try again, or message us on WhatsApp.",
}


# --------------------------------------------------------------------------
# Lead form. Fields and options are the document's Part Two, table 2.
# --------------------------------------------------------------------------

#: ``name``, input type, whether it is required, and where its options come
#: from. Rendered by one template loop, validated by one server-side pass.
LEAD_FIELDS: tuple[dict[str, Any], ...] = (
    {"name": "full_name", "type": "text", "required": True, "maxlength": 120,
     "autocomplete": "name"},
    {"name": "phone", "type": "tel", "required": True, "maxlength": 20,
     "autocomplete": "tel", "dir": "ltr", "inputmode": "tel"},
    {"name": "service", "type": "select", "required": True, "options": "service_options"},
    {"name": "car_model", "type": "text", "required": True, "maxlength": 120},
    {"name": "branch", "type": "select", "required": True, "options": "branch_options"},
    {"name": "timing", "type": "select", "required": True, "options": "timing_options"},
    {"name": "notes", "type": "textarea", "required": False, "maxlength": 2000},
)

LEAD_LABELS = {
    "ar": {
        "full_name": "الاسم الكامل",
        "phone": "رقم الجوال",
        "service": "الخدمة المطلوبة",
        "car_model": "نوع السيارة والموديل",
        "branch": "الفرع المفضل",
        "timing": "متى تفكر بالتنفيذ؟",
        "notes": "ملاحظات",
    },
    "en": {
        "full_name": "Full name",
        "phone": "Phone number",
        "service": "Service you are interested in",
        "car_model": "Car brand / model",
        "branch": "Preferred branch",
        "timing": "When are you thinking of booking?",
        "notes": "Notes",
    },
}

LEAD_HINTS = {
    "ar": {"phone": "رقم سعودي، مثال: 05XXXXXXXX أو +9665XXXXXXXX"},
    "en": {"phone": "Saudi number, e.g. 05XXXXXXXX or +9665XXXXXXXX"},
}

#: Service options. "Not sure yet" is the document's own last option and
#: matters more than it looks: it is the answer from the visitor who most
#: needs a call back.
SERVICE_OPTIONS = {
    "ar": [
        ("ppf-gloss", "حماية PPF لامع"),
        ("ppf-matte", "حماية PPF مطفي"),
        ("nano-ceramic", "نانو سيراميك"),
        ("window-tint", "تظليل عازل حراري"),
        ("colour-change", "تغيير اللون"),
        ("unsure", "لست متأكدًا بعد"),
    ],
    "en": [
        ("ppf-gloss", "PPF Gloss"),
        ("ppf-matte", "PPF Matte"),
        ("nano-ceramic", "Nano Ceramic"),
        ("window-tint", "Window Tint"),
        ("colour-change", "Colour Change"),
        ("unsure", "Not sure yet"),
    ],
}

TIMING_OPTIONS = {
    "ar": [
        ("this-week", "خلال هذا الأسبوع"),
        ("two-weeks", "خلال أسبوعين"),
        ("exploring", "ما زلت أستكشف"),
    ],
    "en": [
        ("this-week", "This week"),
        ("two-weeks", "Within 2 weeks"),
        ("exploring", "Still exploring"),
    ],
}

LEAD_ERRORS = {
    "ar": {
        "required": "هذا الحقل مطلوب.",
        "phone": "أدخل رقم جوال سعودي صحيح.",
        "choice": "اختر أحد الخيارات المتاحة.",
        "too_long": "النص أطول من المسموح.",
        "throttled": "أرسلت طلبًا قبل قليل. انتظر دقيقة ثم حاول مجددًا.",
        "unavailable": "تعذّر حفظ الطلب حاليًا. تواصل معنا على واتساب وسنكمل معك.",
    },
    "en": {
        "required": "This field is required.",
        "phone": "Enter a valid Saudi mobile number.",
        "choice": "Choose one of the available options.",
        "too_long": "That is longer than allowed.",
        "throttled": "You just sent a request. Wait a minute and try again.",
        "unavailable": "We could not save your request right now. Message us on WhatsApp and we will pick it up there.",
    },
}


# --------------------------------------------------------------------------
# Accessors
# --------------------------------------------------------------------------

LOCALES = ("ar", "en")
DEFAULT_LOCALE = "ar"

_BY_LOCALE = {"ar": AR, "en": EN}

#: The database overlay, installed by the application factory once it has a
#: pool to read from. ``None`` in the CLI, in tests, and whenever the site runs
#: without a database — which is the case this module exists to survive.
_OVERLAY: Any = None


def use_overlay(overlay: Any) -> None:
    """Layer stored edits over the shipped copy.

    Called once at start-up. Every accessor below reads through
    :func:`content`, so installing it here is the whole of the swap the plan
    promised: no template and no view changes hands.
    """
    global _OVERLAY
    _OVERLAY = overlay


def shipped(locale: str) -> dict[str, Any]:
    """The copy this repository ships, ignoring anything an editor changed.

    The overlay itself reads through this — merging its rows over
    :func:`content` would call back into the overlay and recurse — and so does
    seeding, which must copy what was written here rather than what is already
    stored.
    """
    return _BY_LOCALE.get(locale, AR)


def content(locale: str) -> dict[str, Any]:
    """Copy for ``locale``, falling back to Arabic.

    With an overlay installed this is the edited copy; without one, or with a
    database that cannot be reached, it is exactly what :func:`shipped`
    returns.
    """
    if _OVERLAY is not None:
        return _OVERLAY.content(locale)
    return shipped(locale)


def _indexed(locale: str, key: str, id_key: str) -> dict[str, Any]:
    return {row[id_key]: row for row in content(locale)[key]}


def service(locale: str, slug: str) -> dict[str, Any] | None:
    return _indexed(locale, "services", "slug").get(slug)


def package(locale: str, slug: str) -> dict[str, Any] | None:
    return _indexed(locale, "packages", "slug").get(slug)


def post(locale: str, slug: str) -> dict[str, Any] | None:
    return _indexed(locale, "posts", "slug").get(slug)


def branch(locale: str, bid: str) -> dict[str, Any] | None:
    return _indexed(locale, "branches", "id").get(bid)


def home_packages(locale: str) -> list[dict[str, Any]]:
    by_slug = _indexed(locale, "packages", "slug")
    return [by_slug[s] for s in HOME_PACKAGES if s in by_slug]


def category_label(locale: str, slug: str) -> str:
    for row in content(locale)["categories"]:
        if row["slug"] == slug:
            return row["label"]
    return slug


def branch_options(locale: str) -> list[tuple[str, str]]:
    """Lead-form branch choices, labelled ``City — Branch``."""
    return [(b["id"], f'{b["city"]} — {b["name"]}') for b in content(locale)["branches"]]


def service_options(locale: str) -> list[tuple[str, str]]:
    return SERVICE_OPTIONS[locale if locale in SERVICE_OPTIONS else DEFAULT_LOCALE]


def timing_options(locale: str) -> list[tuple[str, str]]:
    return TIMING_OPTIONS[locale if locale in TIMING_OPTIONS else DEFAULT_LOCALE]
