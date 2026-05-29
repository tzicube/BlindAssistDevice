import {
  useEffect,
  useMemo,
  useState,
} from "react";

function GridEditor() {
  const rows = 100;
  const cols = 100;

  // create empty grid
  const createEmptyGrid = () =>
    Array(rows)
      .fill(null)
      .map(() =>
        Array(cols)
          .fill(null)
          .map(() => ({
            type: null,
          }))
      );

  // grid
  const [grid, setGrid] = useState(
    createEmptyGrid()
  );

  // zoom
  const [cellSize, setCellSize] =
    useState(24);

  // drawing
  const [isMouseDown, setIsMouseDown] =
    useState(false);

  // selected tool
  const [selectedTool, setSelectedTool] =
    useState("wall");

  // load json from backend
  useEffect(() => {
    async function loadHouse() {
      try {
        const res = await fetch(
          "http://localhost:3000/load-house"
        );

        const parsed =
          await res.json();

        const newGrid =
          createEmptyGrid();

        parsed.rooms.forEach(
          (room) => {
            newGrid[room.row][
              room.col
            ] = {
              type: room.type,
            };
          }
        );

        setGrid(newGrid);
      } catch (error) {
        console.log(
          "No saved json yet"
        );
      }
    }

    loadHouse();
  }, []);

  // excel labels
  const columnLabels = useMemo(() => {
    return Array(cols)
      .fill(null)
      .map((_, i) => {
        let result = "";
        let num = i;

        while (num >= 0) {
          result =
            String.fromCharCode(
              (num % 26) + 65
            ) + result;

          num =
            Math.floor(num / 26) -
            1;
        }

        return result;
      });
  }, []);

  // save json to backend
  async function saveToBackend() {
    const rooms = [];

    grid.forEach(
      (row, rowIndex) => {
        row.forEach(
          (cell, colIndex) => {
            if (cell.type) {
              rooms.push({
                row: rowIndex,
                col: colIndex,
                type: cell.type,
              });
            }
          }
        );
      }
    );

    const jsonData = {
      rooms,
    };

    await fetch(
      "http://localhost:3000/save-house",
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/json",
        },
        body: JSON.stringify(
          jsonData
        ),
      }
    );

    alert("Saved!");
  }

  // paint
  function paintCell(row, col) {
    setGrid((prev) => {
      const newGrid = [...prev];

      newGrid[row] = [
        ...newGrid[row],
      ];

      newGrid[row][col] = {
        type:
          selectedTool ===
          "erase"
            ? null
            : selectedTool,
      };

      return newGrid;
    });
  }

  // drag paint
  function handleMouseEnter(
    row,
    col
  ) {
    if (!isMouseDown) return;

    setGrid((prev) => {
      const newGrid = [...prev];

      newGrid[row] = [
        ...newGrid[row],
      ];

      newGrid[row][col] = {
        type:
          selectedTool ===
          "erase"
            ? null
            : selectedTool,
      };

      return newGrid;
    });
  }

  // zoom
  function handleWheel(e) {
    if (!e.ctrlKey) return;

    e.preventDefault();

    if (e.deltaY < 0) {
      setCellSize((prev) =>
        Math.min(prev + 2, 50)
      );
    } else {
      setCellSize((prev) =>
        Math.max(prev - 2, 10)
      );
    }
  }

  // clear
  function clearGrid() {
    setGrid(createEmptyGrid());
  }

  return (
    <div className="edit-card">
      <h2>Chỉnh sửa nhà</h2>

      <div className="editor-layout">
        {/* GRID */}
        <div
          className="grid-wrapper"
          onWheel={handleWheel}
          onMouseDown={() =>
            setIsMouseDown(true)
          }
          onMouseUp={() =>
            setIsMouseDown(false)
          }
          onMouseLeave={() =>
            setIsMouseDown(false)
          }
        >
          <div
            className="excel-grid"
            style={{
              gridTemplateColumns: `60px repeat(${cols}, ${cellSize}px)`,
            }}
          >
            {/* corner */}
            <div className="corner-cell" />

            {/* columns */}
            {columnLabels.map(
              (label) => (
                <div
                  key={label}
                  className="header-cell"
                  style={{
                    width: cellSize,
                    height: 40,
                  }}
                >
                  {label}
                </div>
              )
            )}

            {/* rows */}
            {grid.map(
              (row, rowIndex) => (
                <>
                  {/* row number */}
                  <div
                    key={`row-${rowIndex}`}
                    className="row-header"
                    style={{
                      height:
                        cellSize,
                    }}
                  >
                    {rowIndex + 1}
                  </div>

                  {/* cells */}
                  {row.map(
                    (
                      cell,
                      colIndex
                    ) => (
                      <div
                        key={`${rowIndex}-${colIndex}`}
                        className={`cell ${
                          cell.type ||
                          ""
                        }`}
                        style={{
                          width:
                            cellSize,
                          height:
                            cellSize,
                        }}
                        onMouseDown={() =>
                          paintCell(
                            rowIndex,
                            colIndex
                          )
                        }
                        onMouseEnter={() =>
                          handleMouseEnter(
                            rowIndex,
                            colIndex
                          )
                        }
                      />
                    )
                  )}
                </>
              )
            )}
          </div>
        </div>

        {/* TOOL PANEL */}
        <div className="tool-panel">
          <h3>Tool Panel</h3>

          {/* WALL */}
          <button
            className={`tool-btn wall-btn ${
              selectedTool ===
              "wall"
                ? "active-tool"
                : ""
            }`}
            onClick={() =>
              setSelectedTool(
                "wall"
              )
            }
          >
            Wall
          </button>

          <br />
          <br />

          {/* BEDROOM */}
          <button
            className={`tool-btn bedroom-btn ${
              selectedTool ===
              "bedroom"
                ? "active-tool"
                : ""
            }`}
            onClick={() =>
              setSelectedTool(
                "bedroom"
              )
            }
          >
            Bedroom
          </button>

          <br />
          <br />

          {/* KITCHEN */}
          <button
            className={`tool-btn kitchen-btn ${
              selectedTool ===
              "kitchen"
                ? "active-tool"
                : ""
            }`}
            onClick={() =>
              setSelectedTool(
                "kitchen"
              )
            }
          >
            Kitchen
          </button>

          <br />
          <br />

          {/* BATHROOM */}
          <button
            className={`tool-btn bathroom-btn ${
              selectedTool ===
              "bathroom"
                ? "active-tool"
                : ""
            }`}
            onClick={() =>
              setSelectedTool(
                "bathroom"
              )
            }
          >
            Bathroom
          </button>

          <br />
          <br />

          {/* DOOR */}
          <button
            className={`tool-btn door-btn ${
              selectedTool ===
              "door"
                ? "active-tool"
                : ""
            }`}
            onClick={() =>
              setSelectedTool(
                "door"
              )
            }
          >
            Door
          </button>

          <br />
          <br />

          {/* ERASE */}
          <button
            className={`tool-btn erase-btn ${
              selectedTool ===
              "erase"
                ? "active-tool"
                : ""
            }`}
            onClick={() =>
              setSelectedTool(
                "erase"
              )
            }
          >
            Erase
          </button>

          <br />
          <br />

          {/* SAVE */}
          <button
            onClick={saveToBackend}
          >
            Save House
          </button>

          <br />
          <br />

          {/* CLEAR */}
          <button
            onClick={clearGrid}
          >
            Clear All
          </button>
        </div>
      </div>
    </div>
  );
}

export default GridEditor;