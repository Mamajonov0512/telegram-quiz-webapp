import os
import json
from pathlib import Path
import openpyxl
from database import init_db, bulk_add_questions, get_questions_count

SAMPLE_QUESTIONS = [
    {
        "question_text": "O'zbekiston Respublikasi davlat mustaqilligi qachon e'lon qilingan?",
        "option_a": "1991-yil 31-avgust",
        "option_b": "1991-yil 1-sentyabr",
        "option_c": "1992-yil 8-dekabr",
        "option_d": "1990-yil 20-iyun",
        "correct_option": "A",
        "explanation": "O'zbekiston Respublikasining davlat mustaqilligi 1991-yil 31-avgustda e'lon qilingan.",
        "category": "Tarix"
    },
    {
        "question_text": "O'zbekiston Respublikasining amaldagi Konstitutsiyasi qachon qabul qilingan (dastlabki)?",
        "option_a": "1991-yil 18-noyabr",
        "option_b": "1992-yil 8-dekabr",
        "option_c": "1993-yil 2-iyul",
        "option_d": "1994-yil 1-iyul",
        "correct_option": "B",
        "explanation": "O'zbekiston Respublikasi Konstitutsiyasi 1992-yil 8-dekabrda qabul qilingan.",
        "category": "Huquq"
    },
    {
        "question_text": "Dunyoning eng baland cho'qqisi qaysi?",
        "option_a": "K2 (Chogori)",
        "option_b": "Kanchenjanga",
        "option_c": "Everest (Jomolungma)",
        "option_d": "Elbrus",
        "correct_option": "C",
        "explanation": "Everest cho'qqisi 8848 metr balandlik bilan dunyoda birinchi o'rinda turadi.",
        "category": "Geografiya"
    },
    {
        "question_text": "Kompyuterning asosiy hisoblash va boshqaruv qurilmasi nima deb ataladi?",
        "option_a": "Operativ xotira (RAM)",
        "option_b": "Markaziy protsessor (CPU)",
        "option_c": "Qattiq disk (HDD/SSD)",
        "option_d": "Videokarta (GPU)",
        "correct_option": "B",
        "explanation": "Markaziy protsessor (CPU) barcha asosiy amallarni bajaruvchi kompyuter 'miyasi' hisoblanadi.",
        "category": "Informatika"
    },
    {
        "question_text": "Alisher Navoiy qaysi asrning buyuk shoiri va mutafakkiri hisoblanadi?",
        "option_a": "XIV asr",
        "option_b": "XV asr",
        "option_c": "XVI asr",
        "option_d": "XVII asr",
        "correct_option": "B",
        "explanation": "Alisher Navoiy 1441-1501-yillarda, ya'ni XV asrda yashab ijod etgan.",
        "category": "Adabiyot"
    },
    {
        "question_text": "Python dasturlash tilida ro'yxat (list) qaysi qavslar yordamida hosil qilinadi?",
        "option_a": "Dumaloq qavs: ( )",
        "option_b": "Figurali qavs: { }",
        "option_c": "Kvadrat qavs: [ ]",
        "option_d": "Burchakli qavs: < >",
        "correct_option": "C",
        "explanation": "Python'da ro'yxatlar kvadrat qavslar [] yordamida yoziladi.",
        "category": "Informatika"
    },
    {
        "question_text": "Quyosh sistemasidagi eng katta sayyora qaysi?",
        "option_a": "Saturn",
        "option_b": "Yupiter",
        "option_c": "Uran",
        "option_d": "Neptun",
        "correct_option": "B",
        "explanation": "Yupiter Quyosh sistemasidagi eng ulkan gaz giganti sayyoradir.",
        "category": "Astronomiya"
    },
    {
        "question_text": "Inson tanasidagi eng katta ichki a'zo qaysi?",
        "option_a": "Yurak",
        "option_b": "O'pka",
        "option_c": "Jigar",
        "option_d": "Buyrak",
        "correct_option": "C",
        "explanation": "Jigar inson organizmidagi eng og'ir va eng katta ichki organdir.",
        "category": "Biologiya"
    },
    {
        "question_text": "Amir Temur qachon va qayerda tavallud topgan?",
        "option_a": "1336-yil Kesh (Shahrisabz)",
        "option_b": "1342-yil Samarqand",
        "option_c": "1328-yil Buxoro",
        "option_d": "1350-yil Toshkent",
        "correct_option": "A",
        "explanation": "Sohibqiron Amir Temur 1336-yil 9-aprelda Shahrisabz yaqinidagi Xo'ja Ilg'or qishlog'ida tug'ilgan.",
        "category": "Tarix"
    },
    {
        "question_text": "Dunyodagi eng chuqur ko'l qaysi?",
        "option_a": "Kaspiy dengizi",
        "option_b": "Viktoriya ko'li",
        "option_c": "Baykal ko'li",
        "option_d": "Tanganika ko'li",
        "correct_option": "C",
        "explanation": "Baykal ko'li 1642 metr chuqurlik bilan dunyodagi eng chuqur chuchuk suv ko'lidir.",
        "category": "Geografiya"
    },
    {
        "question_text": "HTML tili nima maqsadda qo'llaniladi?",
        "option_a": "Ma'lumotlar bazasini boshqarish uchun",
        "option_b": "Veb-sahifaning tuzilishi va skeletini yaratish uchun",
        "option_c": "Server tomonidagi hisob-kitoblar uchun",
        "option_d": "Operatsion tizim yadrosini yozish uchun",
        "correct_option": "B",
        "explanation": "HTML (HyperText Markup Language) gipermatnli belgilash tili bo'lib, veb sahifalar strukturasini beradi.",
        "category": "Informatika"
    },
    {
        "question_text": "Kimyoviy elementlar davriy jadvalining yaratuvchisi kim?",
        "option_a": "Albert Eynshteyn",
        "option_b": "Isaak Nyuton",
        "option_c": "Dmitriy Mendeleyev",
        "option_d": "Nils Bor",
        "correct_option": "C",
        "explanation": "Kimyoviy elementlar davriy qonunini 1869-yilda D.I. Mendeleyev kashf qilgan.",
        "category": "Kimyo"
    },
    {
        "question_text": "O'zbekiston qaysi dengizga to'g'ridan-to'g'ri chiqish yo'liga ega emas?",
        "option_a": "Orol dengiziga",
        "option_b": "Dunyo okeaniga (ikki davlat bilan o'ralgan)",
        "option_c": "Kaspiy dengiziga",
        "option_d": "Qora dengizga",
        "correct_option": "B",
        "explanation": "O'zbekiston va Lixtenshteyn dunyoda okeanga chiqish uchun kamida ikkita davlat chegarasini kesib o'tish talab etiladigan (doubly landlocked) ikki davlatdan biridir.",
        "category": "Geografiya"
    },
    {
        "question_text": "Matematikada doira yuzini topish formulasi qaysi?",
        "option_a": "S = 2 * pi * r",
        "option_b": "S = pi * r^2",
        "option_c": "S = 4/3 * pi * r^3",
        "option_d": "S = a * b",
        "correct_option": "B",
        "explanation": "Doira yuzi S = pi * r^2 formulasi bo'yicha hisoblanadi.",
        "category": "Matematika"
    },
    {
        "question_text": "O'zbekiston milliy valyutasi — 'so'm' qachon muomalaga kiritilgan?",
        "option_a": "1991-yil 1-sentyabr",
        "option_b": "1993-yil 15-noyabr",
        "option_c": "1994-yil 1-iyul",
        "option_d": "1995-yil 1-yanvar",
        "correct_option": "C",
        "explanation": "O'zbekiston milliy valyutasi so'm 1994-yil 1-iyuldan boshlab to'liq muomalaga kiritilgan.",
        "category": "Iqtisodiyot"
    },
    {
        "question_text": "BMT (Birlashgan Millatlar Tashkiloti) qachon tashkil topgan?",
        "option_a": "1918-yil",
        "option_b": "1945-yil",
        "option_c": "1953-yil",
        "option_d": "1960-yil",
        "correct_option": "B",
        "explanation": "BMT 1945-yil 24-oktyabrda San-Fransiskoda tashkil etilgan.",
        "category": "Tarix"
    },
    {
        "question_text": "Yorug'likning vakuumdagi tezligi taxminan qanchaga teng?",
        "option_a": "300 000 km/s",
        "option_b": "150 000 km/s",
        "option_c": "30 000 km/s",
        "option_d": "1 000 000 km/s",
        "correct_option": "A",
        "explanation": "Yorug'lik tezligi vakuumda s taxminan 300 000 km/sekund (aniqrog'i 299 792 458 m/s).",
        "category": "Fizika"
    },
    {
        "question_text": "Internet tarmog'ida ma'lumotlarni xavfsiz (shifrlangan) uzatish protokoli qaysi?",
        "option_a": "HTTP",
        "option_b": "FTP",
        "option_c": "HTTPS",
        "option_d": "SMTP",
        "correct_option": "C",
        "explanation": "HTTPS (Hypertext Transfer Protocol Secure) SSL/TLS orqali shifrlangan xavfsiz protokoldir.",
        "category": "Informatika"
    },
    {
        "question_text": "O'zbekiston Respublikasi davlat bayrog'i qachon qabul qilingan?",
        "option_a": "1991-yil 18-noyabr",
        "option_b": "1992-yil 2-iyul",
        "option_c": "1992-yil 10-dekabr",
        "option_d": "1991-yil 31-avgust",
        "correct_option": "A",
        "explanation": "Davlat bayrog'i to'g'risidagi qonun 1991-yil 18-noyabrda qabul qilingan.",
        "category": "Davlat ramzlari"
    },
    {
        "question_text": "DNK molekulasi tarkibida qaysi azotli asos mavjud emas?",
        "option_a": "Adenin",
        "option_b": "Urasil",
        "option_c": "Guanin",
        "option_d": "Timin",
        "correct_option": "B",
        "explanation": "Urasil faqat RNK molekulasida uchraydi, DNKda uning o'rnida Timin bo'ladi.",
        "category": "Biologiya"
    },
    {
        "question_text": "Qaysi daryo dunyodagi eng sersuv daryo hisoblanadi?",
        "option_a": "Nil",
        "option_b": "Amazonka",
        "option_c": "Yanszi",
        "option_d": "Missisipi",
        "correct_option": "B",
        "explanation": "Amazonka daryosi suv hajmi va havzasi kattaligi bo'yicha dunyoda 1-o'rinda turadi.",
        "category": "Geografiya"
    },
    {
        "question_text": "Kompyuter xotirasining eng kichik o'lchov birligi nima?",
        "option_a": "Bayt",
        "option_b": "Bit",
        "option_c": "Kilobayt",
        "option_d": "Megabayt",
        "correct_option": "B",
        "explanation": "Bit — 0 yoki 1 qiymatini qabul qiluvchi eng kichik axborot o'lchov birligidir. 8 bit = 1 bayt.",
        "category": "Informatika"
    },
    {
        "question_text": "Mirzo Ulug'bek tomonidan Samarqandda qurilgan rasadxona qachon barpo etilgan?",
        "option_a": "1424-1429 yillarda",
        "option_b": "1390-1395 yillarda",
        "option_c": "1450-1455 yillarda",
        "option_d": "1405-1410 yillarda",
        "correct_option": "A",
        "explanation": "Mirzo Ulug'bek rasadxonasi 1424-1429 yillarda Samarqand yaqinidagi Ko'hak tepaligida qurilgan.",
        "category": "Tarix"
    },
    {
        "question_text": "Kvadrat tenglamaning ildizlari sonini aniqlash uchun nima hisoblanadi?",
        "option_a": "Diskriminant (D)",
        "option_b": "Integral",
        "option_c": "Logarifm",
        "option_d": "Faktorial",
        "correct_option": "A",
        "explanation": "Diskriminant D = b^2 - 4ac yordamida kvadrat tenglama ildizlari soni aniqlanadi.",
        "category": "Matematika"
    },
    {
        "question_text": "O'zbekiston Respublikasi davlat gerbi qachon qabul qilingan?",
        "option_a": "1991-yil 18-noyabr",
        "option_b": "1992-yil 2-iyul",
        "option_c": "1992-yil 8-dekabr",
        "option_d": "1993-yil 7-may",
        "correct_option": "B",
        "explanation": "Davlat gerbi haqidagi qonun 1992-yil 2-iyulda Oliy Kengash tomonidan qabul qilingan.",
        "category": "Davlat ramzlari"
    },
    {
        "question_text": "Suvning qaynash harorati normal atmosfera bosimida necha gradus Selsiy?",
        "option_a": "90°C",
        "option_b": "100°C",
        "option_c": "120°C",
        "option_d": "80°C",
        "correct_option": "B",
        "explanation": "Oddiy 1 atmosfera bosimida suv 100 daraja Selsiyda qaynaydi.",
        "category": "Fizika"
    },
    {
        "question_text": "SQL tilida jadvaldan ma'lumotlarni o'qib olish (tanlash) uchun qaysi buyruq ishlatiladi?",
        "option_a": "INSERT",
        "option_b": "UPDATE",
        "option_c": "SELECT",
        "option_d": "DELETE",
        "correct_option": "C",
        "explanation": "SELECT buyrug'i ma'lumotlar bazasidan kerakli yozuvlarni tanlab olish uchun xizmat qiladi.",
        "category": "Informatika"
    },
    {
        "question_text": "Buyuk Ipak yo'lining asosiy yo'nalishlaridan biri qaysi hududlar orqali o'tgan?",
        "option_a": "Shimoliy Amerika",
        "option_b": "Markaziy Osiyo",
        "option_c": "Avstraliya",
        "option_d": "Janubiy Afrika",
        "correct_option": "B",
        "explanation": "Buyuk Ipak yo'li Xitoydan boshlanib Markaziy Osiyo (Samarqand, Buxoro) orqali Yevropaga borgan.",
        "category": "Tarix"
    },
    {
        "question_text": "Avogadro doimiysi qanday qiymatga ega?",
        "option_a": "6.02 * 10^23 mol^-1",
        "option_b": "3.14 * 10^8 mol^-1",
        "option_c": "9.8 m/s^2",
        "option_d": "1.6 * 10^-19 Kl",
        "correct_option": "A",
        "explanation": "1 molda mavjud bo'lgan zarralar soni N_A = 6.022 * 10^23 ga teng.",
        "category": "Kimyo"
    },
    {
        "question_text": "Dunyo okeanining eng katta va eng chuqur qismi qaysi?",
        "option_a": "Atlantika okeani",
        "option_b": "Hind okeani",
        "option_c": "Tinch okeani",
        "option_d": "Shimoliy Muz okeani",
        "correct_option": "C",
        "explanation": "Tinch okeani maydoni va chuqurligi (Mariana botig'i - 11022 m) bo'yicha dunyoda eng kattasidir.",
        "category": "Geografiya"
    },
    {
        "question_text": "O'zbekiston Respublikasi davlat madhiyasi qachon qabul qilingan?",
        "option_a": "1992-yil 10-dekabr",
        "option_b": "1991-yil 1-sentyabr",
        "option_c": "1992-yil 8-dekabr",
        "option_d": "1993-yil 2-iyul",
        "correct_option": "A",
        "explanation": "Davlat madhiyasi to'g'risidagi qonun 1992-yil 10-dekabrda qabul qilingan.",
        "category": "Davlat ramzlari"
    },
    {
        "question_text": "CSS nima uchun ishlatiladi?",
        "option_a": "Ma'lumotlar bazasiga so'rov yuborish uchun",
        "option_b": "Veb sahifalarning dizayni, uslubi va ko'rinishini bezash uchun",
        "option_c": "Server operatsion tizimini boshqarish uchun",
        "option_d": "Fayllarni arxivlash uchun",
        "correct_option": "B",
        "explanation": "CSS (Cascading Style Sheets) veb sahifalarning ranglari, shriftlari va dizaynini belgilash uchun ishlatiladi.",
        "category": "Informatika"
    },
    {
        "question_text": "'O'tkan kunlar' ilk o'zbek romanining muallifi kim?",
        "option_a": "Cho'lpon",
        "option_b": "Abdulla Qodiriy",
        "option_c": "Fitrat",
        "option_d": "Oybek",
        "correct_option": "B",
        "explanation": "Abdulla Qodiriy 1922-yilda 'O'tkan kunlar' romanini yozib o'zbek romanchiligiga asos solgan.",
        "category": "Adabiyot"
    },
    {
        "question_text": "Fotosintez jarayonida o'simliklar havoga qaysi gazni chiqaradi?",
        "option_a": "Karbonat angidrid (CO2)",
        "option_b": "Kislorod (O2)",
        "option_c": "Azot (N2)",
        "option_d": "Metan (CH4)",
        "correct_option": "B",
        "explanation": "Fotosintez jarayonida yashil o'simliklar karbonat angidridni yutib, kislorod ajratib chiqaradi.",
        "category": "Biologiya"
    },
    {
        "question_text": "Yerning tabiiy yo'ldoshi qaysi?",
        "option_a": "Oy",
        "option_b": "Mars",
        "option_c": "Titan",
        "option_d": "Fobos",
        "correct_option": "A",
        "explanation": "Oy — Yerning yagona tabiiy yo'ldoshidir.",
        "category": "Astronomiya"
    },
    {
        "question_text": "JavaScript tilida o'zgarmas o'zgaruvchini e'lon qilish uchun qaysi kalit so'z ishlatiladi?",
        "option_a": "var",
        "option_b": "let",
        "option_c": "const",
        "option_d": "static",
        "correct_option": "C",
        "explanation": "const kalit so'zi qiymati qayta tayinlanmaydigan (o'zgarmas) o'zgaruvchilar uchun ishlatiladi.",
        "category": "Informatika"
    },
    {
        "question_text": "Abu Rayhon Beruniy qaysi fanlarning rivojiga ulkan hissa qo'shgan?",
        "option_a": "Faqat musiqa",
        "option_b": "Astronomiya, matematika, geodeziya va mineralogiya",
        "option_c": "Faqat tasviriy san'at",
        "option_d": "Dasturlash",
        "correct_option": "B",
        "explanation": "Beruniy o'rta asrlarning qomusiy olimi bo'lib, astronomiya, matematika va geodeziyada olamshumul kashfiyotlar qilgan.",
        "category": "Tarix"
    },
    {
        "question_text": "Yer sharida nechta materik (qit'a) mavjud?",
        "option_a": "4 ta",
        "option_b": "5 ta",
        "option_c": "6 ta",
        "option_d": "7 ta",
        "correct_option": "C",
        "explanation": "Yevrosiyo, Afrika, Shimoliy Amerika, Janubiy Amerika, Antarktida, Avstraliya — jami 6 ta materik mavjud.",
        "category": "Geografiya"
    },
    {
        "question_text": "Nyutonning ikkinchi qonuni qaysi formula bilan ifodalanadi?",
        "option_a": "F = m * a",
        "option_b": "E = m * c^2",
        "option_c": "P = F / S",
        "option_d": "v = s / t",
        "correct_option": "A",
        "explanation": "Nyutonning II qonuni: jismga ta'sir qiluvchi kuch uning massasi va olgan tezlanishi ko'paytmasiga teng (F = m*a).",
        "category": "Fizika"
    },
    {
        "question_text": "Ibn Sino (Avitsenna)ning tibbiyotga oid dunyoga mashhur asari nima deb ataladi?",
        "option_a": "Boburnoma",
        "option_b": "Tib qonunlari (Al-Qonun fit-tibb)",
        "option_c": "Ziji Ko'ragoniy",
        "option_d": "Qutadg'u bilig",
        "correct_option": "B",
        "explanation": "Ibn Sinoning 'Tib qonunlari' asari asrlar davomida Sharq va G'arb universitetlarida asosiy qo'llanma bo'lgan.",
        "category": "Tibbiyot"
    },
    {
        "question_text": "Git tizimida o'zgarishlarni yangi commit sifatida saqlashdan oldin qaysi buyruq bilan kiritiladi?",
        "option_a": "git push",
        "option_b": "git add",
        "option_c": "git pull",
        "option_d": "git clone",
        "correct_option": "B",
        "explanation": "git add buyrug'i fayllarni staging areaga qo'shadi, so'ng git commit orqali saqlanadi.",
        "category": "Informatika"
    },
    {
        "question_text": "Quyosh nuri Yergacha taxminan qancha vaqtda yetib keladi?",
        "option_a": "8 soniya",
        "option_b": "8 daqiqa 20 soniya",
        "option_c": "1 soat",
        "option_d": "Bir zumda",
        "correct_option": "B",
        "explanation": "Masofa 150 mln km bo'lgani sababli yorug'lik taxminan 8 daqiqa 20 soniyada yetib keladi.",
        "category": "Astronomiya"
    },
    {
        "question_text": "O'zbekistonda eng baland tog' cho'qqisi qaysi va uning balandligi qancha?",
        "option_a": "Hazrati Sulton (4643 m)",
        "option_b": "Katta Chimyon (3309 m)",
        "option_c": "Adelung (4301 m)",
        "option_d": "Beshtor (4299 m)",
        "correct_option": "A",
        "explanation": "Hisor tizmasidagi Hazrati Sulton cho'qqisi (4643 m) O'zbekistonning eng baland nuqtasidir.",
        "category": "Geografiya"
    },
    {
        "question_text": "Ohm qonunining zanjir qismi uchun formulasi qanday?",
        "option_a": "I = U / R",
        "option_b": "U = I / R",
        "option_c": "R = U * I",
        "option_d": "P = U * I",
        "correct_option": "A",
        "explanation": "Zanjir qismidagi tok kuchi kuchlanishga to'g'ri, qarshilikka teskari mutanosib: I = U / R.",
        "category": "Fizika"
    },
    {
        "question_text": "Algoritmning asosiy xossalariga qaysi biri kirmaydi?",
        "option_a": "Diskretlilik",
        "option_b": "Tushunarlilik",
        "option_c": "Cheksizlik (tugamaslik)",
        "option_d": "Natijaviylik",
        "correct_option": "C",
        "explanation": "Algoritm chekli qadamlardan iborat bo'lishi va albatta natija bilan tugashi (chekllilik va natijaviylik) shart.",
        "category": "Informatika"
    },
    {
        "question_text": "Zahiriddin Muhammad Bobur qaysi sulolaga asos solgan?",
        "option_a": "Temuriylar (Boburiylar / Buyuk Mo'g'ullar davlati)",
        "option_b": "Shayboniylar",
        "option_c": "Somoniylar",
        "option_d": "Saljuqiylar",
        "correct_option": "A",
        "explanation": "Bobur 1526-yilda Hindistonda qudratli Boburiylar davlatiga asos solgan.",
        "category": "Tarix"
    },
    {
        "question_text": "Oddiy osh tuzining kimyoviy formulasi qaysi?",
        "option_a": "NaOH",
        "option_b": "NaCl",
        "option_c": "HCl",
        "option_d": "CaCO3",
        "correct_option": "B",
        "explanation": "Osh tuzi natriy xlorid ya'ni NaCl birikmasidir.",
        "category": "Kimyo"
    },
    {
        "question_text": "Toshkent teleminorasi balandligi qancha metrni tashkil qiladi?",
        "option_a": "375 metr",
        "option_b": "300 metr",
        "option_c": "420 metr",
        "option_d": "250 metr",
        "correct_option": "A",
        "explanation": "Toshkent teleminorasi 375 metr balandlikka ega bo'lib, Markaziy Osiyodagi eng baland inshootlardan biridir.",
        "category": "Umumiy bilim"
    },
    {
        "question_text": "Inson skeletida voyaga yetgan paytda taxminan nechta suyak bo'ladi?",
        "option_a": "150 ta",
        "option_b": "206 ta",
        "option_c": "300 ta",
        "option_d": "250 ta",
        "correct_option": "B",
        "explanation": "Voyaga yetgan inson tanasida taxminan 206 ta suyak mavjud.",
        "category": "Biologiya"
    },
    {
        "question_text": "Telegram messenjerida botlar yaratishda qaysi rasmiy vosita orqali token olinadi?",
        "option_a": "@BotFather",
        "option_b": "@CreatorBot",
        "option_c": "@AdminBot",
        "option_d": "@MasterBot",
        "correct_option": "A",
        "explanation": "Telegram'da yangi bot yaratish va uning API tokenini olish uchun @BotFather botidan foydalaniladi.",
        "category": "Informatika"
    }
]

def seed_database():
    init_db()
    count = get_questions_count()
    if count == 0:
        added = bulk_add_questions(SAMPLE_QUESTIONS)
        print(f"[+] Bazaga {added} ta namunaviy test savollari muvaffaqiyatli yuklandi.")
    else:
        print(f"[*] Bazada allaqachon {count} ta savol mavjud.")

def create_sample_files():
    samples_dir = Path(__file__).resolve().parent / "samples"
    samples_dir.mkdir(exist_ok=True)

    # 1. Excel template
    excel_path = samples_dir / "test_shablon.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Testlar"
    
    # Headers
    headers = ["Savol", "Variant A", "Variant B", "Variant C", "Variant D", "To'g'ri javob", "Izoh", "Kategoriya"]
    ws.append(headers)

    # First 10 questions as sample
    for q in SAMPLE_QUESTIONS[:10]:
        ws.append([
            q["question_text"],
            q["option_a"],
            q["option_b"],
            q["option_c"],
            q["option_d"],
            q["correct_option"],
            q["explanation"],
            q["category"]
        ])
    wb.save(excel_path)
    print(f"[+] Excel shabloni yaratildi: {excel_path}")

    # 2. JSON template
    json_path = samples_dir / "test_shablon.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(SAMPLE_QUESTIONS[:10], f, ensure_ascii=False, indent=2)
    print(f"[+] JSON shabloni yaratildi: {json_path}")

    # 3. TXT template
    txt_path = samples_dir / "test_shablon.txt"
    txt_content = ""
    for idx, q in enumerate(SAMPLE_QUESTIONS[:10], start=1):
        txt_content += f"{idx}. {q['question_text']}\n"
        txt_content += f"A) {q['option_a']}\n"
        txt_content += f"B) {q['option_b']}\n"
        txt_content += f"C) {q['option_c']}\n"
        txt_content += f"D) {q['option_d']}\n"
        txt_content += f"Javob: {q['correct_option']}\n"
        if q['explanation']:
            txt_content += f"Izoh: {q['explanation']}\n"
        txt_content += "\n"

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content.strip())
    print(f"[+] TXT shabloni yaratildi: {txt_path}")

if __name__ == "__main__":
    seed_database()
    create_sample_files()
