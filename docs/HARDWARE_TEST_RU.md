# Проверка на AYN Odin 3 / Armada OS

Первая попытка запуска на Odin 3 остановилась при загрузке `nf_conntrack`:
`Module nf_conntrack not found in directory /lib/modules/6.11.0`.
Изменение v0.1.1 ещё не проверено на устройстве. Перед установкой выполнить
только чтение состояния:

```bash
uname -m
cat /etc/os-release
nft --version
python3 --version
ldd --version
modprobe -n nfnetlink_queue
modprobe -n nft_queue
cat /proc/sys/kernel/osrelease
ls -1 /lib/modules
ls -d /sys/module/{nf_conntrack,nfnetlink_queue,nft_queue}
systemctl status plugin_loader.service --no-pager
```

После подготовки службы через интерфейс плагина:

```bash
systemctl status zapret2-armada.service --no-pager
sudo cat /proc/net/netfilter/nfnetlink_queue
sudo nft list table inet zapret2_armada
sudo journalctl -u zapret2-armada.service -n 80 --no-pager
sudo tail -n 80 /var/log/zapret2-armada/engine.log
```

1. Записать версии Armada, ядра, Decky и условия сети/VPN.
2. Сравнить `sudo nft list ruleset` до/после: изменения допустимы только в
   inet zapret2_armada. Не публиковать полный вывод без просмотра.
3. Проверить Steam, локальные устройства, Proton/FEX игру, YouTube и Discord
   до/после включения. Использовать новые подключения: старые потоки не тест.
4. Проверить домены, исключения, ошибочный JSON и восстановление профиля.
5. Автоподбор должен вернуть исходное состояние и предложить отдельное
   применение результата. HTTPS-проверка не доказывает работу видео/голоса.
6. Включить автозапуск, перезагрузить, проверить профиль и очередь.
7. Сон 2–5 минут → пробуждение → новые подключения. Повторить при смене Wi-Fi.
   Не должно появляться второй очереди/таблицы. Фильтр интерфейсов: wl*.
8. Сравнить FPS/frametime, CPU/RAM, температуру и батарею в одинаковой игре.
   Nice=10, CPUWeight=20, MemoryMax=128M не являются доказательством отсутствия
   влияния на производительность.
9. Кнопка восстановления правил должна остановить только свою службу и
   удалить только свою таблицу, сохранив соединение и остальные правила.
10. Удалить через Decky и повторно проверить Steam, firewall и локальную сеть.

Принудительное завершение nfqws2 на реальном устройстве проводить только
после отдельного согласия на такой аварийный тест. Результаты записать в Issue.
