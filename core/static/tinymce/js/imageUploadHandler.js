function imageUploadHandler(blobInfo, progress) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.withCredentials = false;
        xhr.open('POST', '/api/v1/tinymce/upload');

        xhr.upload.onprogress = (e) => {
            progress(e.loaded / e.total * 100);
        };

        xhr.onload = () => {
            if (xhr.status < 200 || xhr.status >= 300) {
                reject({ message: `HTTP Error: ${xhr.status}`, remove: true });
                return;
            }

            const json = JSON.parse(xhr.responseText);

            if (!json || typeof json.location != 'string') {
                reject(`Invalid JSON: ${xhr.responseText}`);
                return;
            }

            resolve(json.location);
        };

        xhr.onerror = () => {
            reject(`Image upload failed due to a XHR Transport error. Code: ${xhr.status}`);
        };

        const formData = new FormData();
        formData.append('file', blobInfo.blob(), blobInfo.filename());

        xhr.send(formData);
    });
}
