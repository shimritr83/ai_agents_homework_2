# מסמך הסבר — שיעורי בית 2 (מערכת סוכנים מודולרית)

## תיאור הארכיטקטורה

המערכת היא אפליקציית מסוף (CLI) ב־Python המבוססת על **OpenAI Agents SDK**. זרימת העבודה אינה נתב ידני מבוסס `if/else` כארכיטקטורה ראשית: **RouterAgent** הוא סוכן נפרד שמקבל את קלט המשתמש ומבצע **העברה (handoff)** לסוכן המומחה המתאים באמצעות כלי ההעברה של ה־SDK. כל סוכן מומחה מוגדר כ־`Agent` אמיתי עם הוראות, כלים (כאשר נדרש), ו־guardrails על הפלט.

פלט מובנה של הניתוב (`RouterDecision`: כוונה, פרמטרים, רמת ביטחון) מיוצג כאובייקט Pydantic ונרשם ללוג לאחר אימות — בפועל הוא נגזר מ־**payload מובנה של כלי ההעברה** (JSON תקין בזכות סכימה strict), כך שאין צורך בסבב נוסף של מודל רק לניתוב.

הערת SDK: ב־OpenAI Agents SDK ניתן לקבוע `output_type` על `Agent` כדי לקבל פלט מובנה מהמודל. כאשר אותו סוכן הוא גם נקודת כניסה עם `handoffs`, לולאת הריצה עלולה להסתיים בפלט מובנה לפני שמגיעים להעברה. לכן כאן נבחרה גישה בטוחה וחסכונית במודלים: **סכימת JSON של כלי ההעברה + Pydantic** — שקול מבחינת שדות המטלה ל־`RouterDecision`, ותואם את דרישת הלוגים בפועל.

## רשימת הסוכנים ותפקידם

| סוכן | תפקיד |
|------|--------|
| **RouterAgent** | סיווג בקשה, בחירת handoff יחיד, ללא הרצת כלי מזג/מתמטיקה/מטבע בעצמו. |
| **WeatherAgent** | קריאה ל־`get_weather` (Open-Meteo) והחזרת תשובת מזג אוויר קצרה בעברית. |
| **MathAgent** | תרגום בעיות מילוליות לביטוי חשבוני נקי והרצת `calculate_math` בלבד לקבלת תוצאה. |
| **ExchangeRateAgent** | המרה באמצעות `get_exchange_rate` (מיפוי סטטי לפי שווי מטבע בשקלים). |
| **GeneralChatAgent** | שיחה כללית, פרסונה: "עוזר מחקר ציני אך מועיל", עברית קצרה, סירוב מדויק לנושאים אסורים. |

## רשימת הכלים (כלים דטרמיניסטיים)

1. **get_weather** — גיאוקוד Open-Meteo + תחזית `current_weather` (ללא מפתח API).  
2. **calculate_math** — הערכת ביטוי עם `ast` מוגבל (ללא `eval`).  
3. **get_exchange_rate** — המרה לפי טבלת שווי קבועה בשקלים (ILS) לכל מטבע; צמדי צולבנים נגזרים מהיחס בין השוויים (שקול להמרה דרך ILS).

## פירוט ה־handoffs

ה־RouterAgent מחזיק ארבעה אובייקטי `handoff()` של ה־SDK, כל אחד עם `input_type` של Pydantic (למשל עיר וביטחון למזג אוויר). כאשר המודל בוחר העברה, ה־SDK מפעיל את סוכן היעד עם היסטוריית השיחה; ה־hooks (`SubmissionHooks`) מדפיסים שורות `[Handoff] RouterAgent -> …`.

## פירוט ה־input guardrails

1. **EmptyInputGuardrail** — חוסם קלט ריק או רק רווחים; תגובה: `Please enter a valid request.`  
2. **SafetyInputGuardrail** — חוסם פוליטיקה/בקשות קוד זדוני/תוכן לא בטוח לפי heuristics; תגובה מדויקת: `I cannot process this request due to safety protocols.`

שניהם מוגדרים כ־`@input_guardrail` על ה־RouterAgent עם `run_in_parallel=False` כדי שלא יישלח קריאת מודל לפני שמסיימים את הבדיקות.

## פירוט ה־output guardrails

1. **RouterOutputGuardrail (דטרמיניסטי)** — אימות מבנה מול מודל `RouterDecision` והדפסת `[OutputGuardrail] Router output passed` כשהמבנה תקין. הדגמה של חסימה: `python -m app.main --demo-output-guardrail` (ללא API).  
2. **FinalAnswerSafetyGuardrail** — `@output_guardrail` על כל סוכן מומחה; סינון תוכן לא בטוח בפלט.  
3. **NonEmptyFinalAnswerGuardrail** — מוודא שפלט סופי אינו ריק.

לאחר ריצה מוצלחת, ה־runner מדפיס גם `[OutputGuardrail] Final answer passed`.

## ניהול זיכרון

`MemoryManager` טוען את `history.json` בהפעלה, שומר אחרי כל תור משתמש (הודעת משתמש + תשובת עוזר), ותומך ב־`/reset` למחיקה. קטע קצר מההיסטוריה מוזרק ל־**GeneralChatAgent** דרך פונקציית הוראות דינמית (`_general_instructions`) כדי לתמוך במעקב שיחה — בלי לחשוף שרשרת מחשבה ארוכה.

## איך להריץ את המערכת

1. יצירת סביבה וירטואלית והתקנת תלויות (ראו `README.md`).  
2. העתקת `.env.example` ל־`.env` והגדרת `OPENAI_API_KEY`.  
3. הרצה: `python -m app.main` מתיקיית הפרויקט.  
4. פקודות: `/exit`, `/reset`.  
5. הדגמת guardrail על פלט ראוטר פגום: `python -m app.main --demo-output-guardrail`.

---

*אורך המסמך: כ־עמוד וחצי. התאמה להגשה למרצה.*
