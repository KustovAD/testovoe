(function () {
  var RU = {
    "Try it out": "Попробовать",
    "Cancel": "Отмена",
    "Execute": "Выполнить",
    "Clear": "Очистить",
    "Parameters": "Параметры",
    "No parameters": "Без параметров",
    "Name": "Имя",
    "Description": "Описание",
    "Responses": "Ответы",
    "Response body": "Тело ответа",
    "Response headers": "Заголовки ответа",
    "Request URL": "URL запроса",
    "Request body": "Тело запроса",
    "Server response": "Ответ сервера",
    "Code": "Код",
    "Details": "Подробности",
    "Links": "Ссылки",
    "No links": "Нет ссылок",
    "Media type": "Тип содержимого",
    "Controls Accept header.": "Задаёт заголовок Accept.",
    "Example Value": "Пример",
    "Schema": "Схема",
    "Schemas": "Схемы",
    "Servers": "Серверы",
    "Download": "Скачать",
    "Undocumented": "Не задокументирован",
    "Successful Response": "Успешный ответ",
    "Validation Error": "Ошибка валидации",
    "required": "обязательный",
    "Loading...": "Загрузка...",
    "Failed to fetch.": "Не удалось выполнить запрос.",
    "Possible Reasons:": "Возможные причины:",
    "Response content type": "Тип содержимого ответа",
    "Expand all": "Развернуть все",
    "Collapse all": "Свернуть все",
    "Filter by tag": "Фильтр по тегу",
    "Copy to clipboard": "Скопировать"
  };

  function translateNode(node) {
    if (node.nodeType === 3) {
      var t = node.nodeValue.trim();
      if (t && RU[t]) node.nodeValue = node.nodeValue.replace(t, RU[t]);
      return;
    }
    if (node.nodeType !== 1) return;
    if (node.tagName === "INPUT" && RU[node.value]) node.value = RU[node.value];
    if (node.title && RU[node.title]) node.title = RU[node.title];
    var ph = node.getAttribute && node.getAttribute("placeholder");
    if (ph && RU[ph]) node.setAttribute("placeholder", RU[ph]);
    for (var i = 0; i < node.childNodes.length; i++) translateNode(node.childNodes[i]);
  }

  new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
      if (m.type === "characterData") translateNode(m.target);
      m.addedNodes.forEach(translateNode);
    });
  }).observe(document.body, { childList: true, subtree: true, characterData: true });

  translateNode(document.body);
})();
