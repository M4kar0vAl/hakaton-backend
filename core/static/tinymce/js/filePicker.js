function filePicker(cb, value, meta) {
    const input = document.createElement("input");
    input.setAttribute("type", "file");

    switch (meta.filetype) {
        case 'image':
            input.setAttribute("accept", "image/*");
            break;
        case 'media':
            input.setAttribute("accept", "video/*");
            break;
        default:
            break;
    };

    input.addEventListener('change', (e) => {
        const file = e.target.files[0];
        const reader = new FileReader();

        reader.addEventListener('load', () => {
            const id = 'blobid' + (new Date()).getTime();
            const blobCache =  tinymce.activeEditor.editorUpload.blobCache;
            const base64 = reader.result.split(',')[1];
            const blobInfo = blobCache.create(id, file, base64);
            blobCache.add(blobInfo);
            cb(blobInfo.blobUri(), { title: file.name });
        });

        reader.readAsDataURL(file);
    });
    input.click();
}