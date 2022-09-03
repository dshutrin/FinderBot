import vk_api
import config
import utils
import requests
from vk_api.longpoll import VkEventType, VkLongPoll
from models import *
from config import *
from threading import Thread


class MyLongPoll(VkLongPoll):
	def listen(self):
		while True:
			try:
				for event in self.check():
					yield event
			except Exception as error:
				print(error)


class BotBase:
	def __init__(self):
		self.vk_session = vk_api.VkApi(token=token)

	def get_wall_photo_posts(self, wall_id):
		qu = self.vk_session.method('wall.get', {'owner_id': wall_id})
		count = qu['count']

		if count > 100:
			steps = [count//100, count-count//100]
			for i in range(steps[0]):
				posts = self.vk_session.method('wall.get', {'owner_id': wall_id, 'count': 100, 'offset': i})['items']
				for post in posts:
					if 'attachments' in post:
						atts = post['attachments']
						for att in atts:
							if att['type'] == 'photo':
								print(att)
								yield att['photo']
			posts = self.vk_session.method('wall.get', {'owner_id': wall_id, 'count': steps[0], 'offset': steps[1]})['items']
			for post in posts:
				if 'attachments' in post:
					atts = post['attachments']
					for att in atts:
						if att['type'] == 'photo':
							print(att)
							yield att['photo']
		else:
			posts = self.vk_session.method('wall.get', {'owner_id': wall_id, 'count': count})['items']

			for post in posts:
				if 'attachments' in post:
					atts = post['attachments']
					for att in atts:
						if att['type'] == 'photo':
							print(att)
							yield att['photo']

	def init_group_data(self, gid):

		g_name = self.vk_session.method('groups.getById', {'group_id': -gid})[0]['screen_name']

		for item in Photo().select().where(Photo().post_link and Photo().post_link.startswith(f"https://vk.com/{g_name}")):
			item.delete_instance()

		errors = 0
		alls = 0
		added = 0

		for post_info in self.get_wall_photo_posts(gid):  # -174312128
			alls += 1
			pid = f"{post_info['owner_id']}_{post_info['id']}"
			link = f"https://vk.com/{g_name}?z=photo{pid}%2Falbum{post_info['owner_id']}_00%2Frev"  # ссылка на пост
			url = post_info['sizes'][-1]['url']  # ссылка на фото

			try:
				photo = requests.get(url).content
				try:
					Photo().get(photo=photo)
				except Exception as error:
					print(f'Фото не найдено в базе!\n{error}\nДобавляю.')
					Photo(
						photo=photo,
						post_link=link,
						photo_link=post_info['id']
					).save()
					added += 1
				else:
					errors += 1
			except Exception as err:
				print(f'error adding photo: {err}')
				errors += 1

		return f'Всего найдено записей: {alls}\nДобавлено фото: {added}\nОшибок: {errors}'


class VkBot:
	def __init__(self):
		self.vk_session = vk_api.VkApi(token=g_token)
		self.longpoll = MyLongPoll(self.vk_session)
		self.bot_base = BotBase()
		self.clear_key = utils.get_vk_keyboard([])
		self.back_key = utils.get_vk_keyboard([[('Назад', 'красный')]])
		self.adm_menu_key = utils.get_vk_keyboard([
			[('Найти товар по фото', 'зеленый')],
			[('Добавить группу в индекс', 'синий')],
			[('удалить группу из индекса', 'красный')]
		])

	def sender(self, user_id, text, key=utils.get_vk_keyboard([])):
		try:
			self.vk_session.method('messages.send', {'user_id': user_id, 'message': text, 'random_id': 0, 'keyboard': key})
		except Exception as error:
			print(f'1 lvl send error: {error}')
			self.vk_session = vk_api.VkApi(token=g_token)
			try:
				self.vk_session.method('messages.send', {'user_id': user_id, 'message': text, 'random_id': 0, 'keyboard': key})
			except Exception as err:
				print(f'2 lvl send error: {err}')

	def admin_exe(self, event, msg, user_id, user):
		if user.mode == 'start':
			if msg == 'найти товар по фото':
				self.sender(user_id, 'Пришлите фото, чтобы я нашёл товар.', self.back_key)
				user.mode = 'get_photo'
			elif msg == 'добавить группу в индекс':
				self.sender(
					user_id,
					'Пришлите ссылку на группу, чтобы я добавил её в индекс или обновил данные о ней.',
					self.back_key
				)
				user.mode = 'get_g_link'
			elif msg == 'удалить группу из индекса':
				self.sender(
					user_id,
					'Пришлите ссылку на группу, чтобы я удалил её из индекса.',
					self.back_key
				)
				user.mode = 'get_del_g_link'

		elif user.mode == 'get_photo':
			if msg == 'назад':
				self.sender(user_id, 'Выберите действие:', self.adm_menu_key)
				user.mode = 'start'
			else:
				flag = False
				img_data = None
				if len(event.attachments) > 0:
					if event.attachments['attach1_type'] == 'photo':
						msg_info = self.vk_session.method('messages.getById', {'message_ids': event.message_id})
						attach_info = msg_info['items'][0]['attachments'][0]['photo']['sizes'][-1]
						img_data = requests.get(attach_info['url']).content

						with open('n_img.jpg', 'wb') as file:
							file.write(img_data)
						with open('n_img.jpg', 'rb') as file:
							img_data = file.read()

						flag = True
				if flag:
					self.sender(user.vk_id, 'Поиск начался!', self.clear_key)
					ans = utils.get_best_five(img_data)
					if ans:
						self.sender(user_id, '\n'.join(ans), self.adm_menu_key)
					else:
						self.sender(user_id, 'Не удалось найти подходящих изображений.', self.adm_menu_key)
				else:
					self.sender(
						user_id,
						'Не удалось получить информацию об изображении\nПришлите фото заново.',
						self.adm_menu_key
					)
				user.mode = 'start'

		elif user.mode == 'get_g_link':
			if msg == 'назад':
				self.sender(user_id, 'Выберите действие:', self.adm_menu_key)
				user.mode = 'start'
			else:
				try:
					screen_name = msg.replace('https://vk.com/', '').strip()
					g_id = self.vk_session.method('utils.resolveScreenName', {'screen_name': screen_name})['object_id']
					self.sender(user.vk_id, 'Обработка началась!', self.clear_key)
					self.bot_base.init_group_data(-g_id)
					self.sender(user.vk_id, 'Обработка завершилась!', self.adm_menu_key)
				except Exception as error:
					self.sender(user.vk_id, f'Не удалось добавить группу в индекс!\nОшибка: {error}', self.adm_menu_key)
				user.mode = 'start'

		elif user.mode == 'get_del_g_link':
			if msg == 'назад':
				self.sender(user_id, 'Выберите действие:', self.adm_menu_key)
				user.mode = 'start'
			else:
				try:
					screen_name = msg.replace('https://vk.com/', '').strip()
					g_id = self.vk_session.method('utils.resolveScreenName', {'screen_name': screen_name})['object_id']
					self.sender(user.vk_id, 'Обработка началась!', self.clear_key)
					phs = Photo().select()
					for photo in phs:
						if f'https://vk.com/effect_sd?z=photo-{g_id}_' in photo.post_link:
							print(f'DELETE -> {photo.post_link}')
							photo.delete_instance()
					self.sender(user.vk_id, 'Обработка завершилась!', self.adm_menu_key)
				except Exception as error:
					self.sender(user.vk_id, f'Не удалось удалить группу из индекса!\nОшибка: {error}', self.adm_menu_key)
				user.mode = 'start'

		user.save()

	def user_exe(self, event, user_id, user):
		if len(event.attachments) == 0:
			self.sender(user_id, 'Пришлите фото, чтобы я нашёл похожие товары.', self.clear_key)
		else:
			flag = False
			img_data = None
			if len(event.attachments) > 0:
				if event.attachments['attach1_type'] == 'photo':
					msg_info = self.vk_session.method('messages.getById', {'message_ids': event.message_id})
					attach_info = msg_info['items'][0]['attachments'][0]['photo']['sizes'][-1]
					img_data = requests.get(attach_info['url']).content

					with open('n_img.jpg', 'wb') as file:
						file.write(img_data)
					with open('n_img.jpg', 'rb') as file:
						img_data = file.read()

					flag = True
			if flag:
				self.sender(user.vk_id, 'Поиск начался!', self.clear_key)
				ans = utils.get_best_five(img_data)
				if ans:
					self.sender(user_id, '\n'.join(ans), self.clear_key)
				else:
					self.sender(user_id, 'Не удалось найти подходящих изображений.', self.clear_key)
			else:
				self.sender(
					user_id,
					'Не удалось получить информацию об изображении\nПришлите фото заново.',
					self.clear_key
				)
		user.mode = 'start'

	def run(self):
		for event in self.longpoll.listen():
			if (event.type == VkEventType.MESSAGE_NEW) and not event.from_me and not event.from_chat:

				user_id = event.user_id
				msg = event.text.lower()
				user = utils.get_user_by_id(user_id)

				print(user.mode)

				members = utils.get_group_members(self.vk_session, 188446752)

				if not (user_id in members):
					self.sender(user_id, 'Для того, чтобы пользоваться ботом, подпишитесь на группу.', self.clear_key)
				else:
					if msg == 'начать':
						if user_id == config.admin_id:
							self.sender(user_id, 'Выберите действие:', self.adm_menu_key)
						else:
							self.sender(user_id, 'Пришлите фото, чтобы я нашёл для вас подходящие товары', self.clear_key)

					else:
						if user_id == config.admin_id:
							Thread(target=self.admin_exe, args=(event, msg, user_id, user)).start()

						else:
							Thread(target=self.user_exe, args=(event, user_id, user)).start()

					user.save()


if __name__ == '__main__':
	# base = BotBase(); base.init_group_data(-188446752)

	bot = VkBot()
	print('bot started')
	bot.run()
