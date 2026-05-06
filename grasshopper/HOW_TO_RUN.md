# Grasshopper 上手清单 — Rhino 7 试用版（Windows）

> **目标**：用 Rhino + Grasshopper 真正生成 20 个建筑碎片的 OBJ，并保存
> 一份 `millennium_china.gh` Grasshopper 画布以满足"≥ 2 种 3D 软件
> 环境，平台间连续性"的作业要求。
>
> **预计耗时**：下载安装 ~25 min（取决于网速），实际操作 ~10 min。

---

## 第一步 · 安装 Rhino 7（90 天免费试用）

1. 访问 <https://www.rhino3d.com/download/>。
2. 选 **Rhino 7 for Windows** → "Evaluation"（试用版）。如果只看到
   Rhino 8，Rhino 8 也完全可以——本项目代码两版都跑通。
3. 用任意邮箱注册一个 McNeel 账号（免费、无需付款信息），下载安装包。
4. 双击安装，默认选项即可。Grasshopper 自动随 Rhino 一起装好。
5. 启动 Rhino，选择 "Evaluate" 即可使用 90 天。

---

## 第二步 · 打开 Grasshopper 并放一个 GHPython 组件

1. 在 Rhino 命令栏输入 `grasshopper`，回车。Grasshopper 编辑器弹出。
2. 顶部菜单 **Maths → Script → GhPython** ——这是个紫色的组件，把它
   拖到 Grasshopper 画布的空白区域。
3. **右键** GhPython 组件 → **Edit Script…**，弹出代码编辑器。
4. 把 `grasshopper/all_in_one_component.py` 这一整份文件的内容
   **全部** 复制粘贴进去，覆盖掉默认的几行示例代码，点 **OK** 关闭编辑器。

---

## 第三步 · 给两个输入设 Type Hint

1. 在画布上 **右键** GhPython 组件输入端 **`x`** → **Type hint** → **str**。
2. 同样把 **`y`** 的 Type hint 改成 **str**。
   （默认是 ghdoc，必须改成 str，不然 Python 收到的不是字符串。）

---

## 第四步 · 提供两个输入路径

1. 双击画布空白处 → 弹出搜索框，输入 `panel`，回车，画布上出现一个文本面板。
2. 双击该面板，把整段路径粘进去（注意是您本机的真实路径）：

   ```
   E:\Desktop\demo\demo131\outputs\fragments_params\clusters.json
   ```

   把这个面板的输出端连到 GhPython 组件的 **`x`** 输入端。
3. 同理再做一个面板，内容是：

   ```
   E:\Desktop\demo\demo131\outputs\gh_meshes
   ```

   连到 **`y`** 输入端。

---

## 第五步 · 看结果

* 组件运行后，把鼠标悬在它的 **`info`** 输出端上，应该看到类似
  `OK: 20 / 20 meshes built, 20 OBJs exported to E:\Desktop\...\gh_meshes`。
* 如果 GH 组件标题是绿色、没有红/橙色边框，就成功了。
* 在 Rhino 主窗口里，您应该看到 5 × 4 网格上排列的 20 个 mesh —— 鸟巢、
  水立方、CCTV 大楼、上海中心、中国馆五种典型 archetype 各四个变体。
* 文件夹 `outputs\gh_meshes\` 里 20 个 `.obj` 已经被覆盖更新为 Grasshopper 真实产物
  （之前的 trimesh 占位会被覆盖，文件头从 `# trimesh` 变成 `# demo131 millennium-China fragment`）。

---

## 第六步 · 保存 Grasshopper 画布

1. 在 Grasshopper 编辑器里 **File → Save As…**
2. 保存到本仓库下，文件名严格写成
   `E:\Desktop\demo\demo131\grasshopper\millennium_china.gh`
3. 这样 `submission_yujie/design_tool_files/` 里就有 .gh 可以放了。

---

## 第七步 · 重新跑 Blender 动画（用真实 GH 几何）

1. 在 Blender 4.x 的 Scripting workspace 里打开
   `blender/import_and_animate.py`，**Text → Reload**，**Run Script**。
   这次 import 的 OBJ 是 GH 真实产物，几何更丰富。
2. 渲染输出文件名建议改回 `millennium_china.mp4`（在 `render_setup.py`
   里），重渲。

---

## 故障排除

* **错误："cannot import Rhino.Geometry"** — 您不在 Grasshopper 里跑，
  请检查脚本是不是粘进了 GHPython 组件而不是普通 .py 编辑器。
* **错误："`x` is `None`"** — Type hint 没改成 str，或者 panel 没接上。
* **Rhino 顶部弹"Evaluation Expired"** — 试用 90 天已过，可以注册另一个邮箱再申请。
* **想跑 Rhino 8** — 也支持，把 GHPython 组件右键的 `Python 3` 选上即可
  （Rhino 8 默认是 Python 3，本脚本两个版本都通过）。
