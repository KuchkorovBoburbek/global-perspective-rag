# Test uchun 2 tilli yangilik generatsiya qilish prompti

Bu promptni istalgan LLM'ga (ChatGPT, Claude, Gemini va h.k.) kiritib, ikkita
turli tildagi, bir xil mavzudagi, lekin turlicha nuqtai-nazar/framing'ga ega
yangilik maqolalarini oling. Natijani `.txt` ga saqlab (yoki Word/Google Docs
orqali "Print to PDF" qilib) `sample_data/` ga yoki to'g'ridan-to'g'ri ilovaga
Source A / Source B sifatida yuklashingiz mumkin.

---

## PROMPT (nusxa ko'chiring va LLM'ga yuboring)

```
Siz ikki tilli, bitta mavzu bo'yicha, lekin har xil nuqtai-nazar va
framing'ga ega ikkita SINTETIK (o'ylab topilgan, haqiqiy bo'lmagan) yangilik
maqolasini yozib berishingiz kerak. Bu materiallar Retrieval-Augmented
Generation (RAG) ilovasini sinash uchun ishlatiladi — maqsad ikkita manba
o'rtasidagi qarashlar farqini AI orqali tahlil qilishdir.

MAVZU: [BU YERGA MAVZUNI YOZING — masalan: "sun'iy intellektni tartibga
solish", "masofaviy ish rejimi", "elektromobillarga o'tish", "ijtimoiy
tarmoqlarda yosh foydalanuvchilarni himoya qilish" va h.k.]

TIL A: [MASALAN: Inglizcha]
TIL B: [MASALAN: O'zbekcha yoki Ruscha yoki Koreyscha]

Ikkala maqola HAM quyidagi shartlarga javob berishi kerak:

1. Ikkalasi ham xuddi shu voqea/mavzu haqida bo'lishi kerak, lekin ikki
   xil qarash/framing bilan yozilishi kerak:
   - Manba A: [BIRINCHI NUQTAI-NAZAR — masalan: "innovatsiya va tadbirkorlik
     erkinligi" tarafdori, ortiqcha regulyatsiyaga tanqidiy]
   - Manba B: [IKKINCHI NUQTAI-NAZAR — masalan: "iste'molchi/foydalanuvchi
     himoyasi va xavfsizlik" tarafdori, nazoratni zarur deb hisoblovchi]

2. Ikkala maqolada ham BA'ZI umumiy faktlar bo'lishi kerak (masalan, bir xil
   statistika yoki voqea), lekin bu faktlar har xil talqin qilinishi kerak.

3. Har bir maqola kamida 700–1000 so'zdan iborat bo'lishi kerak (uzunroq —
   yaxshiroq, chunki parchalab (chunking) tahlil qilinadi).

4. Har bir maqola boshida albatta quyidagi ogohlantirish bo'lishi shart
   (o'zining tilida):
   "[SINTETIK NAMUNA KONTENT — bu maqola RAG demo loyihasi uchun ta'lim va
   test maqsadida yozilgan. Haqiqiy nashr, jurnalist yoki tashkilotni
   ifodalamaydi.]"

5. Haqiqiy mavjud gazeta/jurnal nomlarini yoki haqiqiy jurnalistlar ismini
   ishlatmang — hammasi o'ylab topilgan bo'lsin.

6. Iqtiboslar (quote) ham o'ylab topilgan bo'lsin, lekin realistik
   ko'rinishda yozilsin (masalan, "bir mutaxassis aytdi..." kabi, ism
   ko'rsatmasdan yoki umumiy sifat bilan).

7. Ikkala maqolani ANIQ ikkita alohida blok sifatida chiqaring:

=== MANBA A (TIL: [TIL A]) ===
[Manba A matni to'liq shu yerda]

=== MANBA B (TIL: [TIL B]) ===
[Manba B matni to'liq shu yerda]

Boshlang.
```

---

## Foydalanish bo'yicha qisqa yo'riqnoma

1. Yuqoridagi promptdagi `[BU YERGA MAVZUNI YOZING]`, `[TIL A]`, `[TIL B]`,
   `[BIRINCHI NUQTAI-NAZAR]`, `[IKKINCHI NUQTAI-NAZAR]` qismlarini o'zingiz
   xohlagan mavzu/tillarga moslab to'ldiring.
2. Promptni istalgan chat LLM'ga yuboring.
3. Chiqqan natijadan "=== MANBA A ===" qismini bitta faylga, "=== MANBA B ==="
   qismini boshqa faylga ajratib saqlang.
4. PDF qilish uchun:
   - Matnni Google Docs yoki Microsoft Word'ga joylang
   - `File → Print → Save as PDF` (yoki `Download → PDF`) qiling
   - Yoki matnni `.txt` holida to'g'ridan-to'g'ri ilovaga yuklashingiz ham
     mumkin — ilova PDF va TXT ikkalasini ham qo'llab-quvvatlaydi.
5. Streamlit ilovasida:
   - Source A ustuniga Manba A faylini yuklang, tilini TIL A qilib tanlang
   - Source B ustuniga Manba B faylini yuklang, tilini TIL B qilib tanlang
   - "📥 문서 처리 및 RAG 생성" tugmasini bosing va tahlil qiling
