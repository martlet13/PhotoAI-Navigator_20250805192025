import React from 'react';

const PhotoDetails = ({ photo }) => {
  if (!photo) {
    return <div>Select a photo to see details.</div>;
  }

  return (
    <div>
      <h2>{photo.name}</h2>
      <img src={photo.url} alt={photo.name} style={{ maxWidth: '100%' }} />
      <div>
        <h3>Tags:</h3>
        <ul>
          {photo.tags.map(tag => (
            <li key={tag}>{tag}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default PhotoDetails;