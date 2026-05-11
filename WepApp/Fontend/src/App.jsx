import React, { useState, useEffect } from "react";
import { Stage, Layer, Rect, Text, Group, Circle } from "react-konva";

export default function App() {
  // 🔹 LOAD localStorage
  const [rooms, setRooms] = useState(() => {
    const saved = localStorage.getItem("rooms");

    return saved
      ? JSON.parse(saved)
      : [
          {
            id: 1,
            name: "Phòng khách",
            x: 50,
            y: 50,
            width: 220,
            height: 160,

            items: [
              {
                id: 1,
                name: "TV",
                x: 40,
                y: 40,
              },

              {
                id: 2,
                name: "Remote",
                x: 120,
                y: 90,
              },
            ],
          },
        ];
  });

  // 🔹 states
  const [selectedRoomId, setSelectedRoomId] = useState(null);

  const [newItem, setNewItem] = useState("");

  const [searchText, setSearchText] = useState("");

  const [searchResult, setSearchResult] = useState("");

  const [targetItemId, setTargetItemId] = useState(null);

  const [editWidth, setEditWidth] = useState("");

  const [editHeight, setEditHeight] = useState("");

  // 🔹 SAVE localStorage
  useEffect(() => {
    localStorage.setItem("rooms", JSON.stringify(rooms));
  }, [rooms]);

  // 🔊 SPEAK
  const speak = (text) => {
    const utterance = new SpeechSynthesisUtterance(text);

    utterance.lang = "vi-VN";

    window.speechSynthesis.speak(utterance);
  };

  // 🔍 SEARCH ITEM
  const handleSearch = () => {
    if (!searchText.trim()) return;

    let foundRoom = null;

    let foundItem = null;

    // loop rooms
    for (let room of rooms) {
      // tìm item trong room
      const item = room.items.find((i) =>
        i.name.toLowerCase().includes(searchText.toLowerCase()),
      );

      // nếu có
      if (item) {
        foundRoom = room;
        foundItem = item;
        break;
      }
    }

    // nếu tìm thấy
    if (foundRoom && foundItem) {
      setSelectedRoomId(foundRoom.id);

      setTargetItemId(foundItem.id);

      const message = `${foundItem.name} ở ${foundRoom.name}`;

      setSearchResult(message);

      speak(message);
    } else {
      const message = `Không tìm thấy ${searchText}`;

      setSearchResult(message);

      setTargetItemId(null);

      speak(message);
    }
  };

  // ➕ ADD ROOM
  const addRoom = () => {
    const newRoom = {
      id: Date.now(),

      name: "Phòng mới",

      x: Math.random() * 300,

      y: Math.random() * 200,

      width: 220,

      height: 160,

      items: [],
    };

    // spread để tạo array mới
    setRooms([...rooms, newRoom]);
  };

  // 👉 SELECT ROOM
  const handleSelectRoom = (room) => {
    setSelectedRoomId(room.id);

    setEditWidth(room.width);

    setEditHeight(room.height);
  };

  // ➕ ADD ITEM
  const handleAddItem = () => {
    if (!selectedRoomId) {
      alert("Chọn phòng trước");
      return;
    }

    if (!newItem.trim()) return;

    const itemObject = {
      id: Date.now(),

      name: newItem,

      // random vị trí trong room
      x: 30 + Math.random() * 120,

      y: 30 + Math.random() * 80,
    };

    setRooms((prevRooms) =>
      prevRooms.map((room) =>
        room.id === selectedRoomId
          ? {
              ...room,

              // tạo items array mới
              items: [...room.items, itemObject],
            }
          : room,
      ),
    );

    setNewItem("");
  };

  // ❌ DELETE ITEM
  const handleDeleteItem = (itemId) => {
    setRooms((prevRooms) =>
      prevRooms.map((room) =>
        room.id === selectedRoomId
          ? {
              ...room,

              // filter tạo array mới
              items: room.items.filter((item) => item.id !== itemId),
            }
          : room,
      ),
    );
  };

  // ❌ DELETE ROOM
  const handleDeleteRoom = () => {
    if (!selectedRoomId) {
      alert("Chọn phòng trước");
      return;
    }

    const confirmDelete = window.confirm("Xóa phòng này?");

    if (!confirmDelete) return;

    // filter để remove room
    const updatedRooms = rooms.filter((room) => room.id !== selectedRoomId);

    setRooms(updatedRooms);

    setSelectedRoomId(null);
  };

  // 🚚 DRAG ROOM
  const handleDragEnd = (e, roomId) => {
    const { x, y } = e.target.position();

    setRooms((prevRooms) =>
      prevRooms.map((room) =>
        room.id === roomId
          ? {
              ...room,
              x,
              y,
            }
          : room,
      ),
    );
  };

  // ✏️ RENAME ROOM
  const handleRenameRoom = () => {
    if (!selectedRoomId) {
      alert("Chọn phòng trước");
      return;
    }

    const newName = prompt("Tên phòng mới:");

    if (!newName) return;

    setRooms((prevRooms) =>
      prevRooms.map((room) =>
        room.id === selectedRoomId
          ? {
              ...room,
              name: newName,
            }
          : room,
      ),
    );
  };

  // 📏 UPDATE SIZE
  const handleUpdateSize = () => {
    if (!selectedRoomId) return;

    setRooms((prevRooms) =>
      prevRooms.map((room) =>
        room.id === selectedRoomId
          ? {
              ...room,

              width: Number(editWidth),

              height: Number(editHeight),
            }
          : room,
      ),
    );
  };

  // room đang selected
  const selectedRoom = rooms.find((room) => room.id === selectedRoomId);

  return (
    <div
      style={{
        display: "flex",
        padding: 10,
        gap: 15,
      }}
    >
      {/* CANVAS */}
      <Stage
        width={700}
        height={500}
        style={{
          border: "2px solid black",
          background: "#f5f5f5",
        }}
      >
        <Layer>
          {rooms.map((room) => (
            <Group
              key={room.id}
              x={room.x}
              y={room.y}
              draggable
              onClick={() => handleSelectRoom(room)}
              onDragEnd={(e) => handleDragEnd(e, room.id)}
            >
              {/* ROOM */}
              <Rect
                width={room.width}
                height={room.height}
                fill={room.id === selectedRoomId ? "#81C784" : "#90CAF9"}
                stroke="black"
                strokeWidth={2}
                cornerRadius={8}
              />

              {/* ROOM NAME */}
              <Text
                text={room.name}
                fontSize={18}
                width={room.width}
                align="center"
                y={10}
              />

              {/* ITEMS */}
              {room.items.map((item) => (
                <Group key={item.id} x={item.x} y={item.y}>
                  {/* ITEM DOT */}
                  <Circle
                    radius={10}
                    fill={item.id === targetItemId ? "red" : "orange"}
                  />

                  {/* ITEM NAME */}
                  <Text text={item.name} x={15} y={-8} fontSize={14} />
                </Group>
              ))}
            </Group>
          ))}
        </Layer>
      </Stage>

      {/* RIGHT PANEL */}
      <div
        style={{
          width: 280,
          border: "1px solid #ccc",
          padding: 10,
          borderRadius: 8,
          background: "white",
        }}
      >
        <h2>📦 Quản lý đồ vật</h2>

        {selectedRoom ? (
          <>
            <h3>{selectedRoom.name}</h3>

            <ul>
              {selectedRoom.items.map((item) => (
                <li key={item.id}>
                  {item.name}

                  <button
                    onClick={() => handleDeleteItem(item.id)}
                    style={{
                      marginLeft: 8,
                    }}
                  >
                    x
                  </button>
                </li>
              ))}
            </ul>

            {/* ADD ITEM */}
            <input
              value={newItem}
              onChange={(e) => setNewItem(e.target.value)}
              placeholder="Tên đồ vật"
            />

            <button onClick={handleAddItem}>Add</button>

            <hr />

            {/* ROOM ACTIONS */}
            <button onClick={handleRenameRoom}>✏️ Đổi tên phòng</button>

            <br />
            <br />

            <button
              onClick={handleDeleteRoom}
              style={{
                background: "red",
                color: "white",
              }}
            >
              🗑 Xóa phòng
            </button>

            <hr />

            {/* SIZE */}
            <h3>📏 Resize Room</h3>

            <input
              type="number"
              value={editWidth}
              onChange={(e) => setEditWidth(e.target.value)}
              placeholder="Width"
            />

            <br />
            <br />

            <input
              type="number"
              value={editHeight}
              onChange={(e) => setEditHeight(e.target.value)}
              placeholder="Height"
            />

            <br />
            <br />

            <button onClick={handleUpdateSize}>Update Size</button>
          </>
        ) : (
          <p>Chọn phòng để chỉnh sửa</p>
        )}

        <hr />

        {/* SEARCH */}
        <h2>🔍 Tìm đồ vật</h2>

        <input
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          placeholder="Ví dụ: TV"
        />

        <button onClick={handleSearch}>Tìm</button>

        <p>{searchResult}</p>

        <hr />

        {/* ADD ROOM */}
        <button onClick={addRoom}>+ Thêm phòng</button>
      </div>
    </div>
  );
}
