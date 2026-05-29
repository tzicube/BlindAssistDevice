function SearchBox() {
  return (
    <div className="card">
      <h2>Tìm kiếm vật cần tìm</h2>

      <input
        type="text"
        placeholder="Nhập tên vật cần tìm..."
      />

      <button>Tìm kiếm</button>
    </div>
  );
}

export default SearchBox;