from PIL import Image
from numpy import asarray, array_equal
from models import *
from json import dumps


def get_vk_keyboard(buts):  # функция создания клавиатур
	nb = []
	for i in range(len(buts)):
		nb.append([])
		for k in range(len(buts[i])):
			color = {'зеленый': 'positive', 'красный': 'negative', 'синий': 'primary', 'белый': 'secondary'}[buts[i][k][1]]
			nb[i].append({
				"action": {"type": "text", "payload": "{\"button\": \"" + "1" + "\"}", "label": f"{buts[i][k][0]}"},
				"color": f"{color}"
			})
	return str(dumps({'one_time': False, 'buttons': nb}, ensure_ascii=False).encode('utf-8').decode('utf-8'))


def get_per(im1, im2):
	"""Нужно передать бинарное значение фотографий"""
	with open('im1.jpg', 'wb') as f:
		f.write(im1)
	with open('im2.jpg', 'wb') as f:
		f.write(im2)

	im1_l = asarray(Image.open('im1.jpg').convert('RGB'))
	im2_l = asarray(Image.open('im2.jpg').convert('RGB'))

	if array_equal(im1_l, im2_l):
		return 100

	im1_l = list(im1_l.tolist())
	im2_l = list(im2_l.tolist())

	al = 0
	eq = 0
	print(len(im1_l), len(im1_l[0]), "  ", len(im2_l), len(im2_l[0]))
	for i in range(min(len(im2_l), len(im1_l))):
		for k in range(min(len(im2_l[i]), len(im1_l[i]))):
			for point in range(min(len(im2_l[i][k]), len(im1_l[i][k]))):
				al += 1
				if abs(im1_l[i][k][point] - im2_l[i][k][point]) < 10:
					eq += 1
	return (eq/al)*100


def get_best_five(img):
	top = [0, 0, 0, 0, 0]
	items = [None, None, None, None, None]
	for photo in [x for x in Photo().select()]:
		coef = get_per(photo.photo, img)
		print(coef)
		if coef > 50:
			for i in reversed(range(len(top))):
				if top[i] < coef:
					for m in range(1, len(top)-1):
						for k in reversed(range(i, len(top)-m)):
							if k != 4:
								top[k+1] = top[k]
								items[k+1] = items[k]
						top[i] = coef
						items[i] = photo.post_link
						if items[i] in items[i+1:len(items)]:
							items[i+1:len(items)] = [None]*len(items[i+1:len(items)])
							top[i+1:len(items)] = [0] * len(items[i+1:len(items)])
	return list(set([x for x in items if x]))


def get_user_by_id(user_id):
	try:
		return User().get(vk_id=user_id)
	except Exception as error:
		print(f'{error}Пользователь не найден в базе данных!\nДобавляю.')
		User(
			vk_id=user_id,
			mode='start'
		).save()
		return User().get(vk_id=user_id)


def get_group_members(vk_session, g_id):
	users_info = vk_session.method('groups.getMembers', {'group_id': g_id})
	count = users_info["count"]
	members = users_info["items"]
	offset = 1000

	while offset < count:
		users_info = vk_session.method('groups.getMembers', {"group_id": 188446752, "count": count, "offset": offset})
		offset = users_info["offset"]
		members += users_info["members"]

	return members


if __name__ == '__main__':
	print(
		get_per(
			Photo().get(id=1).photo,
			Photo().get(id=2).photo,
		)
	)
