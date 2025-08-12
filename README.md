# Pin-it-Go (Forked from [Pin-it](https://github.com/nelsonGX/pin-it))

# showcase

![image](https://github.com/user-attachments/assets/9bf08dd0-e0a8-415e-9bd8-b418cedb781c)

## 專案簡介

Pin-it-Go 是一個使用 Go 語言編寫的 Discord 機器人，旨在讓伺服器成員透過投票來釘選（Pin）頻道中的重要訊息。

**運作流程：**
1.  **觸發：** 當使用者想要釘選某則訊息時，只需「回覆」該訊息，並在回覆內容中「提及」（mention）Pin-it 機器人。
2.  **啟動投票：** 機器人被觸發後，會立即在該則「回覆」上加入三個表情符號（Reactions）：一個 `✅`、一個 `slash` emoji，以及一個代表釘選所需票數的「數字 emoji」。這個數字由 `CONFIRM_CAP` 環境變數決定。
3.  **進行投票：** 其他成員（或觸發者本人）可以點擊該「數字 emoji」來進行投票。
4.  **成功釘選：** 當點擊「數字 emoji」的票數達到 `CONFIRM_CAP` 設定的門檻時，機器人就會自動將最初「被回覆」的那則訊息釘選起來。

## 環境設定

在執行此應用程式之前，您需要先設定好環境變數。

1.  複製專案中的 `.env.example` 檔案，並將其重新命名為 `.env`。
2.  開啟 `.env` 檔案，並填入以下必要的資訊：

    *   `TOKEN`: 這是您的 Discord 機器人權杖（Token）。您需要前往 [Discord Developer Portal](https://discord.com/developers/applications) 建立一個新的應用程式並取得您的機器人權杖。
        ```
        TOKEN="在此貼上您的Discord機器人權杖"
        ```

    *   `CONFIRM_CAP`: 這是成功釘選訊息所需的最低票數。機器人會根據此數字顯示對應的「數字 emoji」作為投票按鈕。例如，若設定為 `2`，使用者就需要點擊數字 `2` 的 emoji 來投票，當票數達到 2 票時，訊息便會被釘選。如果此值設定為 `0`，則提及機器人後，訊息將被直接釘選，無需投票。
        ```
        CONFIRM_CAP=2
        ```

## 如何執行

請確認您的電腦已安裝 Go 語言環境。

1.  開啟您的終端機（Terminal）。
2.  使用 `cd` 指令切換到專案的根目錄。
3.  執行以下指令來編譯並啟動應用程式：

    ```bash
    go run main.go
    ```

4.  成功執行後，您會在終端機看到 "Bot is now running. Press CTRL-C to exit." 的訊息，表示機器人已成功上線。

### 優化編譯 (產生更小的執行檔)

如果您需要一個體積更小的執行檔，可以使用以下指令進行編譯。這個指令會移除除錯資訊，大幅縮小檔案大小：

```sh
go build -ldflags="-s -w" -o bot main.go
```

### 執行編譯檔

編譯完成後，會在專案根目錄下產生一個名為 `bot` 的執行檔。
在終端機中，使用以下指令即可執行它：

```sh
./bot
```

