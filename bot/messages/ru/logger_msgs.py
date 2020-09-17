# ============================== log_template ===============================
from discord.ext.commands import errors

pm_name = "Приват"

command_success = "{user} использовал команду '{command}'"

command_fail = "{user} неправильно использовал команду '{command}'. {fail_msg}."

user_answer = "{user} сделал выбор '{choice}' в команде '{command}'."

cog_launched = "Винтик {cog_name} был загружен."

bot_restarted = "Бот был незапланированно перезагружен. Могут возникнуть проблемы с рейдом."

command_error = "{user} совершил ошибку в команде '{command}'. {error}."

unknown_command_error = "{user} совершил неизвестную ошибку в команде '{command}."

role_from_reaction = "{guild}: {user} {'получил' if is_get else 'убрал'} роль {role} через реакцию {reaction}."

reaction = "{guild}/{channel}: {user} использовал реакцию {emoji}. {msg}."

notify_success = "Рейд выплывающий в {time_leaving} был оповещён об скором отплытии. {amount} оповещено. "

# ============================== commands.events ===============================

bot_ready = 'Бот к рабскому труду готов!'

user_notification_on = "{user} включил оповещение о скором рейде."

user_notification_off = "{user} отключил оповещение о скором рейде."

# ============================== commands.base ===============================

command_not_found = 'Команда не найдена'

wrong_channel = 'Неправильный канал'

# ============================== commands.raid_manager.creation ===============================

raid_not_found = 'Рейд не найден'

raids_not_found = 'Рейды не найдены'

raid_exist = 'Рейд с такими параметрами уже существует'

user_not_response = 'Пользователь не ответил на поставленный вопрос'

captain_not_exist = 'Капитан не был найден'

# ============================== commands.raid_manager.joining ===============================

no_registration = 'Нету регистрации'

already_in_raid = 'Уже в рейдею'

raid_is_full = 'Рейд заполнен'

already_in_same_raid = 'Пользователь уже в похожем рейде'

raid_joining = 'Пользователь попал в рейд к капитану {captain_name}'

raid_leaving = 'Пользователь покинул рейд капитан {captain_name}'

no_available_raids = 'Нету доступных рейдов'

nope_in_raids = 'Нету в рейдах'

logs_not_found = 'Логи не найдены'

# ============================== commands.raid_manager.registration ===============================

already_registered = 'Уже зарегистрирован'

# ============================== Errors ===============================

errors_name = {
    errors.BadArgument: 'Плохие аргументы',
    errors.CheckFailure: 'Проверка провалена',
    errors.MissingRequiredArgument: 'Нету необходимых аргументов',
    errors.CommandNotFound: 'Команда не найдена',
    errors.PrivateMessageOnly: 'Только в приватные сообщения',
    errors.NoPrivateMessage: 'Только не в приватные сообщения',
    errors.BotMissingPermissions: 'У бота нету необходимых прав',
    errors.UserInputError: 'Проблема пользовательского ввода',
}
