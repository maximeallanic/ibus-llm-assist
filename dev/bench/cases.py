"""Bench cases in four scripts and writing directions, made up for the bench: text beginnings to complete, faulty
sentences with the accepted corrections, and correct sentences that must come back unchanged. Apostrophes are
accepted in both forms."""

COMPLETIONS = {
    'fr': ['Bonjour, je voudrais', 'Merci beaucoup pour', 'Je te rappelle', 'Le rendez-vous est prévu',
           'Pourriez-vous m’envoyer', 'Nous sommes heureux de', 'Je suis désolé, mais', 'À quelle heure'],
    'en': ['Thank you so much for', 'I would like to', 'Please let me know', 'The meeting has been',
           'Could you send me', 'We are happy to', 'Sorry, but I', 'What time does'],
    'ja': ['お世話になって', 'よろしくお願い', '明日の会議は', 'ご連絡ありがとう', '少々お待ち', '今日は天気が',
           '駅までの道を', '申し訳ございませんが'],
    'ar': ['شكرا جزيلا على', 'أود أن', 'يرجى إعلامي', 'الاجتماع سيكون', 'هل يمكنك أن', 'نحن سعداء',
           'آسف، لكن', 'في أي ساعة'],
}

FAULTY = {
    'fr': [
        ('Il a ete tres content.', ['Il a été très content.']),
        ('Les enfant jouent dehors.', ['Les enfants jouent dehors.']),
        ('Je suis allé a la plage.', ['Je suis allé à la plage.']),
        ('Elle sont parties hier.', ['Elles sont parties hier.']),
        ('Nous avons manger ensemble.', ['Nous avons mangé ensemble.']),
        ('Ces une bonne idée.', ["C'est une bonne idée.", 'C’est une bonne idée.']),
        ('Il faut que tu vien demain.', ['Il faut que tu viennes demain.']),
        ('Quel heure est-il ?', ['Quelle heure est-il ?', 'Quelle heure est-il\u202f?', 'Quelle heure est-il?']),
    ],
    'en': [
        ('I has a car.', ['I have a car.']),
        ('She dont like coffee.', ["She doesn't like coffee.", 'She doesn’t like coffee.']),
        ('Their going to the park.', ["They're going to the park.", 'They’re going to the park.']),
        ('He recieved the letter.', ['He received the letter.']),
        ('We was late yesterday.', ['We were late yesterday.']),
        ('The dogs is barking.', ['The dogs are barking.']),
        ('Its a beautiful day.', ["It's a beautiful day.", 'It’s a beautiful day.']),
        ('I definately agree.', ['I definitely agree.']),
    ],
    'ja': [
        ('私わ学生です。', ['私は学生です。']),
        ('駅えの道を教えてください。', ['駅への道を教えてください。']),
        ('明日わ休みです。', ['明日は休みです。']),
        ('東京え行きます。', ['東京へ行きます。']),
        ('これわ私の本です。', ['これは私の本です。']),
        ('水を飲みたいでず。', ['水を飲みたいです。']),
        ('こんにちわ、元気ですか。', ['こんにちは、元気ですか。']),
        ('日本の首都わ東京です。', ['日本の首都は東京です。']),
    ],
    'ar': [
        ('هذه مدرسه كبيرة.', ['هذه مدرسة كبيرة.']),
        ('انا احب القراءة.', ['أنا أحب القراءة.']),
        ('ذهبت الى السوق.', ['ذهبت إلى السوق.']),
        ('سافرنا الى مصر.', ['سافرنا إلى مصر.']),
        ('هل انت جاهز؟', ['هل أنت جاهز؟']),
        ('المدينه جميلة جدا.', ['المدينة جميلة جدا.', 'المدينة جميلة جدًا.', 'المدينة جميلة جداً.']),
        ('اكلت التفاحه.', ['أكلت التفاحة.']),
        ('هو يدرس فى الجامعة.', ['هو يدرس في الجامعة.']),
    ],
}

CORRECT = {
    'fr': ['Le chat dort sur le canapé.', 'Nous partons demain matin.', 'Merci pour ton aide.',
           'Il pleut depuis ce matin.'],
    'en': ['The meeting starts at noon.', 'I will call you tomorrow.', 'Thanks for your help.',
           'She lives near the station.'],
    'ja': ['今日はいい天気です。', '電車が遅れました。', 'ありがとうございます。', 'この本は面白いです。'],
    'ar': ['أنا أحب القهوة.', 'الطقس جميل اليوم.', 'أين المكتبة؟', 'هذا كتاب جديد.'],
}
