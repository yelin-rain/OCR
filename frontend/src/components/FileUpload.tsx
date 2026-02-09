import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Loader2 } from 'lucide-react';
import { cn } from '../utils/utils';
import { message } from 'antd';

interface FileUploadProps {
    onUpload: (file: File, onProgress: (percent: number) => void) => Promise<void>;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onUpload }) => {
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState(0);

    const onDrop = useCallback(async (acceptedFiles: File[]) => {
        const file = acceptedFiles[0];
        if (!file) return;

        setUploading(true);
        try {
            await onUpload(file, (percent) => setProgress(percent));
            message.success('图片上传成功，开始识别');
        } catch (error) {
            console.error("Upload failed", error);
            message.error("上传失败，请检查后端连接");
        } finally {
            setUploading(false);
            setProgress(0);
        }
    }, [onUpload]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'image/*': ['.png', '.jpg', '.jpeg', '.bmp']
        },
        multiple: false
    });

    return (
        <div
            {...getRootProps()}
            className={cn(
                "border-2 border-dashed rounded-xl p-10 transition-all duration-300 cursor-pointer flex flex-col items-center justify-center gap-4 group",
                isDragActive
                    ? "border-blue-500 bg-blue-500/10 scale-[1.02]"
                    : "border-gray-600 hover:border-blue-400 hover:bg-gray-800/50 bg-gray-900/50"
            )}
        >
            <input {...getInputProps()} />

            <div className="relative">
                <div className={cn(
                    "p-4 rounded-full bg-blue-500/20 text-blue-400 transition-transform duration-300",
                    isDragActive ? "scale-110" : "group-hover:scale-110"
                )}>
                    {uploading ? (
                        <Loader2 className="w-8 h-8 animate-spin" />
                    ) : (
                        <Upload className="w-8 h-8" />
                    )}
                </div>
            </div>

            <div className="text-center space-y-2">
                <h3 className="text-lg font-semibold text-gray-200">
                    {uploading ? "正在上传..." : "点击或拖拽图片到此处"}
                </h3>
                <p className="text-sm text-gray-400">
                    {uploading ? `${progress}%` : "支持 JPG, PNG, BMP 格式"}
                </p>
            </div>

            {uploading && (
                <div className="w-full h-1 bg-gray-700 rounded-full overflow-hidden mt-4 max-w-xs">
                    <div
                        className="h-full bg-blue-500 transition-all duration-300"
                        style={{ width: `${progress}%` }}
                    />
                </div>
            )}
        </div>
    );
};
