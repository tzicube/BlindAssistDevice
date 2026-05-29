import SearchBox from "../components/SearchBox";
import GuideBox from "../components/GuideBox";
import CameraView from "../components/CameraView";

import "../styles/home.css";

function Home() {
  return (
    <div className="home-page">
      <div className="left-panel">
        <SearchBox />
        <GuideBox />
      </div>

      <div className="camera-panel">
        <CameraView />
      </div>
    </div>
  );
}

export default Home;