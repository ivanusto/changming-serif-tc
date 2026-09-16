昌明體 ChangMing Serif TC 1.1.0：網頁字型包（分片版）

這個資料夾適合任何網站使用（不需要 WordPress）。字型已依常用字切成許多小檔，
瀏覽器只會下載頁面實際用到的字。

== 內容 ==
changming/changming.css       字型宣告（常用字與英文，請直接載入）
changming/changming-tail.css  罕用字的字型宣告（建議非阻塞載入）
changming/fonts/              分片字型檔（400 與 700 兩個字重）
example.html                  範例頁，放上網站或本機伺服器後即可開啟
OFL.txt                       字型授權

== 使用方式 ==
1. 把 changming/ 整個資料夾上傳到網站，例如放在 /assets/changming/。
   資料夾內的相對路徑不要更動。

2. 在每個頁面的 <head> 加入（路徑依實際位置調整）：

   <link rel="preload" href="/assets/changming/fonts/cmsr-400-l0.1733afae.woff2" as="font" type="font/woff2" crossorigin>
   <link rel="preload" href="/assets/changming/fonts/cmsr-400-h0.4cd24b30.woff2" as="font" type="font/woff2" crossorigin>
   <link rel="stylesheet" href="/assets/changming/changming.css">
   <link rel="stylesheet" href="/assets/changming/changming-tail.css" media="print" onload="this.media='all'">

   前兩行 preload 可省略，保留會讓英文與最常用中文更早顯示。

3. 在自己的 CSS 指定字型：

   body { font-family: "ChangMing Serif TC", Georgia, serif; }
   h1, h2, h3 { font-weight: 700; }   /* 只有 400 與 700 兩個字重 */

   若英文想維持原本的字型，把昌明體放在英文字型之後即可：
   body { font-family: "Helvetica Neue", Arial, "ChangMing Serif TC", serif; }

== 注意 ==
- 請直接用 http(s) 開啟頁面。用 file:// 直接開啟 HTML 時，部分瀏覽器會擋下字型。
- 字型放在其他網域（例如 CDN）時，該網域要允許跨來源載入字型（CORS）。
- 檔名含內容雜湊，可以設定長期快取。

== 授權 ==
字型依 SIL Open Font License 1.1 授權（見 OFL.txt）。
昌明體修改自 Noto Serif TC，並從 Noto Serif CJK TC 與源樣明體（GenYo Min 2）
補入台語、客語用字，(c) 2014-2024 Adobe。Noto 是 Google 的商標。
專案：https://github.com/ivanusto/changming-serif-tc
