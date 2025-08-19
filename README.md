# 本程式是Youtube和Twitch的二合一聊天室(只有顯示功能)
# 無需登入，只要url即可! 


本程式建構於 90% Grok + 10% 人工修正，  
原Python開發，以Auto-py-to-exe轉換為windows即開即用軟件。  

## 使用方法:
1. 先下載Youtube-Twitch-Chatroom-mix.zip 
2. 解壓縮，打開Youtube Twitch Chatroom mix.exe即可 

首次啟動會自動下載emoji和Youtube emoji(未支援twitch emoji)

## *關於如何支援會員頻道訂閱的emoji(如圖)
1. 使用F12(開發者工具)，點開直播/待直播的聊天室😊(即笑臉) 
2. 點擊指向左上角的箭頭(選取網頁中的元素即可檢查)，或者按下Ctrl + Shift + C
3. 像這張圖，指到剛好是紫色框框，每一個格都有框好頻道會員emoji，然後移動右邊div id="emoji"，右鍵複製元素。 
![image](https://github.com/mise39/Youtube-Twitch-Chatroom-mix/blob/main/teach01.jpg)
4. 貼在記事本，並改名字叫div.txt
5. 下載YT_member_emoji_output.exe，並打開它。
6. 你會得到一個extra_emojis_任意名字.txt
7. 放在Youtube Twitch Chatroom mix.exe同一目錄下即可，下一次啟動會自動抓取。
## *若抓取失敗，可到emoji_download_log.txt查看，有可能短時間抓取太多次被Ban IP。
