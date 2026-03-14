/**
 * Beautiful Confirmation Dialog Component
 */
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { AlertTriangle, Info, CheckCircle, Trash2, Save, LayoutList, PlusCircle } from "lucide-react";
import { ReactNode } from "react";

export type ConfirmDialogType = "delete" | "update" | "reorder" | "add" | "warning" | "info";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  title: string;
  description: string;
  type?: ConfirmDialogType;
  confirmText?: string;
  cancelText?: string;
}

const iconStyles = {
  delete: "text-red-500 bg-red-100 dark:bg-red-900/20",
  update: "text-blue-500 bg-blue-100 dark:bg-blue-900/20",
  reorder: "text-purple-500 bg-purple-100 dark:bg-purple-900/20",
  add: "text-green-500 bg-green-100 dark:bg-green-900/20",
  warning: "text-yellow-500 bg-yellow-100 dark:bg-yellow-900/20",
  info: "text-blue-500 bg-blue-100 dark:bg-blue-900/20",
};

const icons = {
  delete: <Trash2 className="w-6 h-6" />,
  update: <Save className="w-6 h-6" />,
  reorder: <LayoutList className="w-6 h-6" />,
  add: <PlusCircle className="w-6 h-6" />,
  warning: <AlertTriangle className="w-6 h-6" />,
  info: <Info className="w-6 h-6" />,
};

const defaultConfirmText = {
  delete: "Delete",
  update: "Save",
  reorder: "Reorder",
  add: "Add",
  warning: "Continue",
  info: "OK",
};

const defaultCancelText = "Cancel";

export function ConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
  title,
  description,
  type = "info",
  confirmText,
  cancelText = defaultCancelText,
}: ConfirmDialogProps) {
  const handleConfirm = () => {
    onConfirm();
    onOpenChange(false);
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className={`p-2 rounded-full ${iconStyles[type]}`}>
              {icons[type]}
            </div>
            <AlertDialogTitle className="text-lg">{title}</AlertDialogTitle>
          </div>
          <AlertDialogDescription className="text-base ml-11">
            {description}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="ml-11">
          <AlertDialogCancel>{cancelText}</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            className={type === "delete" ? "bg-red-500 hover:bg-red-600" : ""}
          >
            {confirmText || defaultConfirmText[type]}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

/**
 * Hook for showing confirmation dialogs
 */
import { useState, useCallback } from "react";

interface UseConfirmDialogReturn {
  showDialog: (props: Omit<ConfirmDialogProps, "open" | "onOpenChange" | "onConfirm">) => Promise<boolean>;
  dialogProps: ConfirmDialogProps & { open: boolean; onOpenChange: (open: boolean) => void; onConfirm: () => void };
}

export function useConfirmDialog(): UseConfirmDialogReturn {
  const [dialogState, setDialogState] = useState<{
    open: boolean;
    props: Omit<ConfirmDialogProps, "open" | "onOpenChange" | "onConfirm">;
  }>({
    open: false,
    props: {
      title: "",
      description: "",
      type: "info",
    },
  });

  const [resolvePromise, setResolvePromise] = useState<(value: boolean) => void | null>(null);

  const showDialog = useCallback(
    (props: Omit<ConfirmDialogProps, "open" | "onOpenChange" | "onConfirm">): Promise<boolean> => {
      return new Promise((resolve) => {
        setDialogState({
          open: true,
          props,
        });
        setResolvePromise(() => resolve);
      });
    },
    []
  );

  const handleConfirm = useCallback(() => {
    resolvePromise?.(true);
    setDialogState((prev) => ({ ...prev, open: false }));
  }, [resolvePromise]);

  const handleCancel = useCallback(() => {
    resolvePromise?.(false);
    setDialogState((prev) => ({ ...prev, open: false }));
  }, [resolvePromise]);

  return {
    showDialog,
    dialogProps: {
      ...dialogState.props,
      open: dialogState.open,
      onOpenChange: (open) => {
        if (!open) handleCancel();
        setDialogState((prev) => ({ ...prev, open }));
      },
      onConfirm: handleConfirm,
    },
  };
}
